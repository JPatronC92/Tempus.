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
            headers={"X-API-Key": API_KEY}
        )
        semantic_context = semantic_res.json()
        print(f"   ✅ Contexto recuperado en {semantic_context.get('processing_time_ms', 0)}ms")
        
    except Exception as e:
        print(f"   ⚠️ Error en Semantic: {e}")
        semantic_context = {"error": str(e), "results": []}

    # PASO 2: Evaluación Determinista y Registro (Tempus Engine)
    print("\n⚖️  2. Sometiendo a Evaluación Determinista (Tempus Engine / Decision Database)...")
    print("   [En desarrollo: Aquí el Agent Orchestrator transformaría el contexto semántico en un JSON estructurado para enviarlo a Tempus]")
    print("   [Tempus evaluará, firmará criptográficamente la decisión, y la guardará inmutablemente en PostgreSQL]")

    print("\n✅ Proceso completado simulado.")

if __name__ == "__main__":
    # Simulación de un agente solicitando aprobar un crédito
    query_decision_infrastructure(
        query_text="El cliente solicita un crédito de $15000. Su historial de impagos es de 2 eventos en los últimos 5 años.",
        agent_id="llm-risk-assessor-v2"
    )
