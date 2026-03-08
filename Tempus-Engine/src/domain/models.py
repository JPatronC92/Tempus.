import uuid as uuid_pkg
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, ForeignKey,
    Integer, DateTime, Boolean
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, DATERANGE
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import ExcludeConstraint

class Base(DeclarativeBase):
    pass

class Tenant(Base):
    """Organización o empresa dueña de las reglas de pricing."""
    __tablename__ = "tenants"

    id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    api_keys = relationship("APIKey", back_populates="tenant", cascade="all, delete-orphan")
    schemes = relationship("PricingScheme", back_populates="tenant", cascade="all, delete-orphan")
    context_schemas = relationship("PricingContextSchema", back_populates="tenant", cascade="all, delete-orphan")

class APIKey(Base):
    """Clave de acceso para la integración B2B vía SDK."""
    __tablename__ = "api_keys"

    id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    tenant_id: Mapped[uuid_pkg.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    key_hash: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    tenant = relationship("Tenant", back_populates="api_keys")


class PricingContextSchema(Base):
    """Schema JSON para validar el payload de la transacción antes de cobrar."""
    __tablename__ = "pricing_context_schemas"

    id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    tenant_id: Mapped[uuid_pkg.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, index=True) # Removed unique=True because names can repeat across tenants
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    schema_json: Mapped[dict] = mapped_column(JSONB, nullable=False)

    tenant = relationship("Tenant", back_populates="context_schemas")

class PricingScheme(Base):
    """Agrupa múltiples reglas. Ej: 'Marketplace Standard MX', 'Enterprise VIP'"""
    __tablename__ = "pricing_schemes"

    id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    tenant_id: Mapped[uuid_pkg.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    urn: Mapped[str] = mapped_column(String, unique=True, index=True) # Ej: urn:pricing:marketplace:mx
    name: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(String)
    
    tenant = relationship("Tenant", back_populates="schemes")
    rules = relationship("PricingRuleIdentity", back_populates="scheme", cascade="all, delete-orphan")

class PricingRuleIdentity(Base):
    """La identidad inmutable de un cargo. Ej: 'Comisión Tarjeta de Crédito'"""
    __tablename__ = "pricing_rule_identities"
    
    uuid: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    scheme_id: Mapped[uuid_pkg.UUID] = mapped_column(ForeignKey("pricing_schemes.id"), nullable=False)
    name: Mapped[str] = mapped_column(String)
    fee_type: Mapped[str] = mapped_column(String) # PERCENTAGE, FIXED_FEE, TIERED
    
    scheme = relationship("PricingScheme", back_populates="rules")
    versiones = relationship("PricingRuleVersion", back_populates="rule", cascade="all, delete-orphan")

class PricingRuleVersion(Base):
    """El corazón: La versión histórica y determinista de la regla matemática."""
    __tablename__ = "pricing_rule_versions"

    id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    rule_uuid: Mapped[uuid_pkg.UUID] = mapped_column(ForeignKey("pricing_rule_identities.uuid"), nullable=False)
    schema_id: Mapped[uuid_pkg.UUID] = mapped_column(ForeignKey("pricing_context_schemas.id"), nullable=False)
    
    # json-logic que DEBE evaluar y retornar un NÚMERO (El monto del fee)
    logica_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    vigencia: Mapped[object] = mapped_column(DATERANGE, nullable=False)
    hash_firma: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Trazabilidad criptográfica
    hash_algoritmo: Mapped[str] = mapped_column(String(20), nullable=False, default="SHA-256")
    
    rule = relationship("PricingRuleIdentity", back_populates="versiones")
    context_schema = relationship("PricingContextSchema")

    # Time-Travel Constraint: Imposible solapar versiones de la misma regla
    __table_args__ = (
        ExcludeConstraint(
            ('rule_uuid', '='),
            ('vigencia', '&&'),
            name='no_solapamiento_temporal_pricing'
        ),
    )

@event.listens_for(PricingRuleVersion, "before_update")
def prevent_update(mapper, connection, target):
    raise IntegrityError(
        statement=None,
        params=None,
        orig="PricingRuleVersion is immutable. Modifying historical financial rules is strictly prohibited. Create a new version instead.",
    )

class DecisionRecord(Base):
    """
    El corazón de la Decision Database (DDB). 
    No guarda estados, guarda la estructura causal completa de un proceso de decisión.
    """
    __tablename__ = "decision_records"

    # La identidad de la decisión en sí
    id: Mapped[uuid_pkg.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pkg.uuid4)
    tenant_id: Mapped[uuid_pkg.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    
    # 1. El actor (¿Quién o qué modelo la tomó?)
    agent_identity: Mapped[str] = mapped_column(String, index=True) # Ej: "llm-risk-assessor-v4" o "human:jpatron"
    
    # 2. El Contexto Semántico (¿Qué información se consideró?)
    semantic_context: Mapped[dict] = mapped_column(JSONB, nullable=True) 
    
    # 3. La Regla Determinista (¿Bajo qué ley se juzgó?)
    rule_version_id: Mapped[uuid_pkg.UUID] = mapped_column(ForeignKey("pricing_rule_versions.id"), nullable=False)
    
    # 4. Los Inputs (¿Qué variables entraron al motor Tempus?)
    input_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    # 5. El Outcome (La decisión matemática final y el estado de gobernanza)
    computed_output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    governance_status: Mapped[str] = mapped_column(String, index=True) # "APPROVED", "BLOCKED_BY_GUARDRAIL"
    
    # 6. Trazabilidad Temporal Inmutable
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)
    execution_latency_ms: Mapped[float] = mapped_column(nullable=True)
    
    # Sello criptográfico de toda la decisión
    cryptographic_receipt: Mapped[str] = mapped_column(String, unique=True, index=True)

    rule_version = relationship("PricingRuleVersion")

@event.listens_for(DecisionRecord, "before_update")
def prevent_decision_update(mapper, connection, target):
    raise IntegrityError(
        statement=None,
        params=None,
        orig="DecisionRecord is immutable. Modifying historical decision records violates AI Governance compliance.",
    )

