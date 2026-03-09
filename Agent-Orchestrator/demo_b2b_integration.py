"""
Demo: B2B Integration with Tempus SDK
This script demonstrates how a 3rd party corporate client (e.g., a Bank or Hospital)
integrates their AI system with the Tempus Decision Database using the new Python SDK.
"""

import sys
import os

# For the sake of the demo, we add the local tempus-python folder to the path
# In a real scenario, the client would just run `pip install tempus-sdk`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../Tempus-Engine/tempus-python')))

# 1. Import the SDK
from tempus_sdk import TempusClient

def run_integration_demo():
    print("🚀 Iniciando Integración B2B con Tempus SDK...\n")

    # 2. Inicializar el Cliente
    print("[1] Conectando con Tempus Decision Database...")
    client = TempusClient(api_url="http://localhost:8001/api/v1")
    print("    Conexión establecida.\n")

    # 3. Simular un Agente LLM Corporativo tomando una decisión
    print("[2] Agente Financiero (GPT-4) solicita evaluar un préstamo...")
    
    agent_id = "Corporate-Finance-Bot-v2"
    rule_name = "credit_policy_v1"
    context = {"doc_id": "profile_998", "risk_tier": "B"}
    input_data = {
        "credit_score": 720,
        "amount": 15000,
        "is_internal": False
    }

    try:
        # 4. Enviar la decisión a Tempus DDB
        response = client.request_decision(
            agent_id=agent_id,
            rule_name=rule_name,
            context=context,
            input_data=input_data
        )
        
        receipt = response.get("receipt")
        status = "APROBADA" if response.get("approved") else "BLOQUEADA"
        
        print(f"    Resultado de Gobernanza: [{status}]")
        print(f"    Razón: {response.get('reason')}")
        print(f"    🛡️ RECIBO CRIPTOGRÁFICO EMITIDO: {receipt}\n")
        
        # 5. Auditoría Inmediata
        print(f"[3] Auditando Recibo Criptográfico B2B: {receipt[:12]}...")
        audit_response = client.audit_receipt(receipt)
        
        if audit_response.get("status") == "VALID":
            print(f"    ✅ Integridad Matematicamente Verificada.")
            print(f"       (Auditado en: {audit_response.get('verified_at')})")
        else:
            print(f"    ❌ ALERTA: Fallo de Integridad.")

    except Exception as e:
        print(f"\n[!] Error en la integración B2B: {str(e)}")
        print("    Asegúrate de que la API de Tempus está corriendo en localhost:8001")


if __name__ == "__main__":
    run_integration_demo()
