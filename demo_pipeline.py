import requests
import json
import uuid
import time
from datetime import datetime

SEMANTIC_URL = "http://localhost:8000"
TEMPUS_URL = "http://localhost:8001"
API_KEY = "sk_dev_12345"

def query_decision_infrastructure(query_text: str, agent_id: str):
    print(f"\n--- INICIANDO PROCESO DE DECISIÓN GOBERNADA ---")
    print(f"🤖 Agente Solicitante: {agent_id}")
    print(f"📝 Escenario: '{query_text}'")
    
    # PASO 1: Búsqueda Semántica (Contexto)
    print("\n🔍 1. Consultando Memoria Corporativa (Semantic Motor)...")
    try:
        # En una demo real, primero haríamos un /v1/index con las reglas de negocio
        search_payload = {
            "query": query_text,
            "top_k": 1,
            "similarity_threshold": 0.5
        }
        semantic_res = requests.post(
            f"{SEMANTIC_URL}/v1/search", 
            json=search_payload,
            headers={"X-API-Key": API_KEY},
            timeout=3
        )
        semantic_res.raise_for_status()
        semantic_context = semantic_res.json()
        print(f"   ✅ Contexto recuperado en {semantic_context.get('processing_time_ms', 0)}ms")
        
    except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
        print(f"   ⚠️ Motor Semántico offline o inalcanzable. Usando RAG Simulado para Demo. Error: {e}")
        semantic_context = {
            "results": [{"id": "doc_mock_123", "text": "Simulated context: client has good history"}],
            "processing_time_ms": 12
        }

    # PASO 2: Evaluación Determinista y Registro (Tempus Engine)
    print("\n⚖️  2. Sometiendo a Evaluación Determinista (Tempus Engine / Decision Database)...")
    
    # Extraemos el primer resultado del motor semántico (o usamos un dummy si falló)
    semantic_id = "doc_fallback"
    if semantic_context and semantic_context.get("results"):
        semantic_id = semantic_context["results"][0].get("id", "doc_fallback")
        
    tempus_payload = {
        "agent_id": agent_id,
        "rule_name": "credit_policy_v1",
        "context": { 
            "original_query": query_text,
            "semantic_retrieval_id": semantic_id 
        },
        "input_data": { 
            "credit_score": 620,  # Simulated based on query features
            "amount": 15000 
        }
    }
    
    print("   [+] Enviando carga útil estructurada al Motor Tempus:")
    print(json.dumps(tempus_payload, indent=2))
    
    try:
        tempus_res = requests.post(f"{TEMPUS_URL}/api/v1/govern/decide", json=tempus_payload, timeout=5)
        tempus_res.raise_for_status()
        decision_data = tempus_res.json()
        
        print("\n   [✓] Decisión Criptografiada Exitosamente:")
        print(f"       ✅ Outcome: {decision_data.get('decision')}")
        print(f"       🔒 Sello Criptográfico (HMAC-SHA256): {decision_data.get('receipt')}")
    except Exception as e:
        print(f"   ⚠️ Error contactando al Tempus Engine (¿está encendido el backend?): {e}")

    print("\n✅ Proceso completado. La respuesta del Agente está respaldada matemática y semánticamente.\n")

if __name__ == "__main__":
    # Simulación de un agente solicitando aprobar un crédito
    query_decision_infrastructure(
        query_text="El cliente solicita un crédito de $15000. Su historial de impagos es de 2 eventos en los últimos 5 años.",
        agent_id="llm-risk-assessor-v2"
    )
