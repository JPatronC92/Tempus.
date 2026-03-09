from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import hashlib
import hmac
import json
import time
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi.responses import StreamingResponse
import asyncio
from src.infrastructure.database import AsyncSessionLocal

from src.interfaces.api.dependencies import SessionDep
from src.domain.models import DecisionRecord, PricingRuleIdentity, PricingRuleVersion

from json_logic import jsonLogic

try:
    import tempus_core
    RUST_CORE_AVAILABLE = True
except ImportError:
    RUST_CORE_AVAILABLE = False

from src.domain.services.crypto import generate_hmac, verify_hmac

router = APIRouter()

class DecisionRequest(BaseModel):
    agent_id: str = Field(..., description="ID del Agente de IA que solicita la decisión.")
    rule_name: str = Field(..., description="Nombre de la regla a aplicar (ej. 'credit_policy_v1').")
    context: dict = Field(..., description="Contexto semántico recuperado por el agente.")
    input_data: dict = Field(..., description="Los datos de entrada para la evaluación.")

class DecisionResponse(BaseModel):
    decision: dict
    receipt: str

@router.post("/decide", response_model=DecisionResponse, summary="Evalúa y registra una decisión inmutable.")
async def decide(payload: DecisionRequest, db: SessionDep):
    start_time = time.perf_counter()

    # 1. Resolver versión de la regla por nombre (Para demo, buscamos la más reciente)
    stmt = (
        select(PricingRuleVersion)
        .join(PricingRuleIdentity)
        .where(PricingRuleIdentity.name == payload.rule_name)
        .order_by(PricingRuleVersion.evaluated_at.desc() if hasattr(PricingRuleVersion, 'evaluated_at') else PricingRuleVersion.id.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    rule_version = result.scalar_one_or_none()

    if not rule_version:
        # Fallback for demo: Si no existe, usamos una regla dummy para no bloquear la demo
        dummy_logic = {
            "if": [
                {"<": [{"var": "credit_score"}, 600]},
                {"approved": False, "reason": "credit_score_too_low"},
                {"approved": True, "reason": "meets_criteria"}
            ]
        }
        logica_json = dummy_logic
        rule_version_id = None # Ojo, en prod debe fallar si no hay regla.
    else:
        logica_json = rule_version.logica_json
        rule_version_id = rule_version.id

    # 2. Ejecutar el motor en Rust
    if RUST_CORE_AVAILABLE:
        try:
            # TEMPUS_CORE devuelve float. Adaptamos para que pueda devolver objetos json_logic si es necesario, 
            # o simulamos la ejecución en Python si la regla devuelve un dict (Tempus Core actual está optimizado para fees numéricos)
            output = jsonLogic(logica_json, payload.input_data)
        except Exception as e:
            output = {"error": str(e)}
    else:
        output = jsonLogic(logica_json, payload.input_data)

    if not isinstance(output, dict):
        output = {"result": output}

    timestamp = int(time.time())

    # 3. Construir el payload del recibo
    receipt_payload = {
        "agent_id": payload.agent_id,
        "rule_name": payload.rule_name,
        "input": payload.input_data,
        "output": output,
        "timestamp": timestamp
    }

    receipt_bytes = json.dumps(receipt_payload, sort_keys=True).encode()

    # 4. Generar HMAC SHA256 (Recibo criptográfico)
    receipt = generate_hmac(receipt_bytes)

    end_time = time.perf_counter()
    latency_ms = (end_time - start_time) * 1000

    # 5. Persistir en la Decision Database
    if rule_version_id: # Solo persistimos si resolvimos una regla real (para que la BD no falle por ForeignKey)
        # Obtenemos el tenant de la regla
        stmt_tenant = select(PricingRuleIdentity).where(PricingRuleIdentity.uuid == rule_version.rule_uuid)
        res_tenant = await db.execute(stmt_tenant)
        identity = res_tenant.scalar_one()
        stmt_scheme = select(PricingRuleIdentity.scheme_id).where(PricingRuleIdentity.uuid == identity.uuid)
        # Simplificación para la demo: asumimos que tenant_id está accesible o inyectamos uno por defecto.
        # Por ahora creamos un record. Si falla, es porque falta tenant_id. 
        # En una demo real lo sacaríamos de la API_KEY.
        pass

    # Para la DEMO aseguramos que el insert funcione:
    # Como tenant_id es requerido, buscaremos el primero que exista o crearemos uno.
    from src.domain.models import Tenant
    stmt_tenant = select(Tenant).limit(1)
    res_tenant = await db.execute(stmt_tenant)
    tenant = res_tenant.scalar_one_or_none()
    
    if not tenant:
        tenant = Tenant(name="Demo Corp")
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)

    # Si no había rule_version, creamos una para la demo para satisfacer la FK
    if not rule_version_id:
        from src.domain.models import PricingScheme, PricingContextSchema
        # Need a scheme
        stmt_scheme = select(PricingScheme).limit(1)
        scheme = (await db.execute(stmt_scheme)).scalar_one_or_none()
        if not scheme:
            scheme = PricingScheme(tenant_id=tenant.id, urn="urn:demo:scheme", name="Demo Scheme")
            db.add(scheme)
            await db.commit()
            await db.refresh(scheme)
            
        # Need a context schema
        stmt_ctx = select(PricingContextSchema).limit(1)
        ctx = (await db.execute(stmt_ctx)).scalar_one_or_none()
        if not ctx:
            ctx = PricingContextSchema(tenant_id=tenant.id, name="Demo Ctx", schema_json={})
            db.add(ctx)
            await db.commit()
            await db.refresh(ctx)

        identity = PricingRuleIdentity(scheme_id=scheme.id, name=payload.rule_name, fee_type="CUSTOM")
        db.add(identity)
        await db.commit()
        await db.refresh(identity)
        
        from datetime import date
        rule_version = PricingRuleVersion(
            rule_uuid=identity.uuid,
            schema_id=ctx.id,
            logica_json=logica_json,
            vigencia=(date(2020, 1, 1), None)
        )
        db.add(rule_version)
        await db.commit()
        await db.refresh(rule_version)
        rule_version_id = rule_version.id

    record = DecisionRecord(
        tenant_id=tenant.id,
        agent_identity=payload.agent_id,
        semantic_context=payload.context,
        rule_version_id=rule_version_id,
        input_data=payload.input_data,
        computed_output=output,
        governance_status="APPROVED",
        cryptographic_receipt=receipt,
        execution_latency_ms=latency_ms,
        evaluated_at=datetime.utcfromtimestamp(timestamp)
    )

    db.add(record)
    await db.commit()

    return DecisionResponse(
        decision=output,
        receipt=receipt
    )


@router.get("/audit/{receipt}", summary="Verifica criptográficamente un recibo de decisión.")
async def audit_decision(receipt: str, db: SessionDep):
    stmt = select(DecisionRecord).where(DecisionRecord.cryptographic_receipt == receipt)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="Recibo no encontrado en la Decision Database.")

    # Reconstruir el nombre de la regla
    stmt_rule = select(PricingRuleIdentity.name).join(PricingRuleVersion).where(PricingRuleVersion.id == record.rule_version_id)
    rule_name = (await db.execute(stmt_rule)).scalar_one()

    # Reconstruir el timestamp exacto que se usó al crear el recibo
    # Como lo guardamos con utcfromtimestamp, aplicamos timestamp() 
    # Aseguramos que sea int (podría tener decimales menores por precisiones en bd)
    timestamp = int(record.evaluated_at.replace(microsecond=0).timestamp())
    
    # 1. Reconstruir el payload exacto
    receipt_payload = {
        "agent_id": record.agent_identity,
        "rule_name": rule_name,
        "input": record.input_data,
        "output": record.computed_output,
        "timestamp": timestamp
    }
    receipt_bytes = json.dumps(receipt_payload, sort_keys=True).encode()

    # 2. Verificar HMAC e integridad (seguro contra ataques de timing internamente)
    is_valid = verify_hmac(receipt_bytes, receipt)
    
    if is_valid:
        status = "VALID"
    else:
        status = "TAMPERED"

    return {
        "status": status,
        "verified_at": datetime.utcnow().isoformat(),
        "decision_record": {
            "agent_id": record.agent_identity,
            "rule_name": rule_name,
            "latency_ms": record.execution_latency_ms,
            "timestamp": record.evaluated_at.isoformat()
        }
    }

@router.get("/explain/{receipt}", summary="Reconstruye la traza completa de una decisión.")
async def explain_decision(receipt: str, db: SessionDep):
    stmt = select(DecisionRecord).where(DecisionRecord.cryptographic_receipt == receipt)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="Recibo no encontrado.")

    stmt_rule = select(PricingRuleIdentity.name).join(PricingRuleVersion).where(PricingRuleVersion.id == record.rule_version_id)
    rule_name = (await db.execute(stmt_rule)).scalar_one()

    return {
        "Decision Trace": {
            "Agent": record.agent_identity,
            "Rule Version": rule_name,
            "Input": record.input_data,
            "Output": record.computed_output,
            "Receipt": record.cryptographic_receipt,
            "Governance Status": record.governance_status,
            "Execution Time": f"{record.execution_latency_ms:.2f} ms",
            "Timestamp": record.evaluated_at.isoformat()
        }
    }


@router.get("/decisions", summary="Obtiene el historial de decisiones para el Decision Explorer.")
async def list_decisions(db: SessionDep, limit: int = 50):
    stmt = select(DecisionRecord).order_by(DecisionRecord.evaluated_at.desc()).limit(limit)
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    decisions = []
    for r in records:
        decisions.append({
            "id": str(r.id),
            "agent_identity": r.agent_identity,
            "governance_status": r.governance_status,
            "rule_version_id": str(r.rule_version_id),
            "computed_output": r.computed_output,
            "cryptographic_receipt": r.cryptographic_receipt,
            "execution_latency_ms": r.execution_latency_ms,
            "evaluated_at": r.evaluated_at.isoformat()
        })
    return {"decisions": decisions}

@router.get("/decisions/stream", summary="Obtiene el historial de decisiones en tiempo real usando Server-Sent Events (SSE).")
async def stream_decisions():
    async def event_generator():
        last_seen_id = None
        while True:
            try:
                async with AsyncSessionLocal() as session:
                    # Traer los registros recientes
                    stmt = select(DecisionRecord).order_by(DecisionRecord.evaluated_at.desc()).limit(20)
                    result = await session.execute(stmt)
                    records = result.scalars().all()
                    
                    if records:
                        latest = records[0]
                        if latest.id != last_seen_id:
                            last_seen_id = latest.id
                            decisions = []
                            for r in records:
                                decisions.append({
                                    "id": str(r.id),
                                    "agent_identity": r.agent_identity,
                                    "governance_status": r.governance_status,
                                    "rule_version_id": str(r.rule_version_id),
                                    "computed_output": r.computed_output,
                                    "cryptographic_receipt": r.cryptographic_receipt,
                                    "execution_latency_ms": r.execution_latency_ms,
                                    "evaluated_at": r.evaluated_at.isoformat()
                                })
                            
                            # Entregar datos con formato SSE
                            yield f"data: {json.dumps({'decisions': decisions})}\n\n"
            except Exception as e:
                pass # Evitar romper el stream por un pequeño fallo de conexión DB
            
            await asyncio.sleep(1) # Intervalo robusto para SSE demo

    return StreamingResponse(event_generator(), media_type="text/event-stream")

