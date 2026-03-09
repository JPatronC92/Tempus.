import urllib.request
import json
import time
import subprocess
import os

# Configuración
# Asumimos que el backend de Tempus corre en el puerto 8001 para la demo
API_URL = "http://localhost:8001/api/v1/govern"

def print_step(title):
    print(f"\n{'='*70}")
    print(f"{title.upper()}")
    print(f"{'='*70}\n")

def main():
    print("🎬 Bienvenido a la Master Demo de Tempus Decision Database")
    print("Esta demostración unifica el ciclo de vida de una decisión inmutable.\n")

    # ==========================================
    # ACTO 1: EL AGENTE ACTÚA
    # ==========================================
    print_step("Acto 1: Generando una Decisión (El Agente de IA Actúa)")
    
    payload = {
        "agent_id": "loan-assessor-ai",
        "rule_name": "credit_policy_v1",
        "context": {"doc": "user_profile_123"},
        "input_data": {"credit_score": 750, "amount": 50000}
    }
    
    data_json = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(f"{API_URL}/decide", data=data_json, headers={'Content-Type': 'application/json'})
    
    print(f"🤖 El Agente evalúa la solicitud crediticia:")
    print(json.dumps(payload, indent=2))
    print(f"\n📡 Enviando solicitud al motor Tempus...")
    
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res_body = response.read().decode('utf-8')
            data = json.loads(res_body)
    except Exception as e:
        print(f"❌ Error al generar decisión (¿está encendido el backend en {API_URL}?): {e}")
        return
        
    receipt = data.get("receipt")
    decision = data.get("decision")
    
    print(f"\n[+] Decisión Tomada por Tempus: {decision}")
    print(f"[+] 🔒 Sello Criptográfico Inquebrantable (HMAC-SHA256): {receipt}")
    time.sleep(2)
    
    # ==========================================
    # ACTO 2: LA GOBERNANZA
    # ==========================================
    print_step("Acto 2: Auditoría Normal (El Tribunal Revisa)")
    print(f"⚖️ Verificando el recibo en la base de datos inmutable: {receipt[:16]}...")
    
    try:
        with urllib.request.urlopen(f"{API_URL}/audit/{receipt}", timeout=5) as audit_res:
            audit_data = json.loads(audit_res.read().decode('utf-8'))
    except Exception as e:
        print("❌ Error en auditoría inicial:", e)
        return
    
    if audit_data.get("status") == "VALID":
        print("\n[✓] Auditoría Exitosa: El registro es íntegro y auténtico.")
    else:
        print("\n[✗] Fallo en la auditoría inicial. Algo no cuadra.")
        
    time.sleep(3)
    
    # ==========================================
    # ACTO 3: EL ATAQUE
    # ==========================================
    print_step("Acto 3: El Ataque (Simulando un DBA corrupto)")
    print("😈 Conectando directamente a la base de datos PostgreSQL mediante Docker...")
    print("Un hacker o administrador intenta cambiar el resultado de 'approved: True' a 'false' ocultando su huella.\n")
    
    hacked_output = '{"reason": "corrupted_by_hacker", "approved": false}'
    
    # Se usa docker exec para inyectar SQL directamente, emulando acceso privilegiado a la DB
    sql_command = f"""
    UPDATE decision_records 
    SET computed_output = '{hacked_output}' 
    WHERE cryptographic_receipt = '{receipt}';
    """
    
    docker_cmd = [
        "docker", "exec", "tempus-db", "psql", 
        "-U", "postgres", "-d", "tempus_db", "-c", sql_command
    ]
    
    try:
        result = subprocess.run(docker_cmd, capture_output=True, text=True)
        if result.returncode == 0 and "UPDATE 1" in result.stdout:
            print(f"[!] INTRUSIÓN EXITOSA 🥷")
            print(f"La fila fue modificada directamente en PostgreSQL (bypass de la aplicación).")
            print(f"Nuevo Output (Manipulado): {hacked_output}")
            print(f"El recibo criptográfico NO ha sido actualizado (el atacante no tiene la llave secreta).")
        else:
            print(f"❌ Error modificando DB o el contenedor 'tempus-db' no existe: {result.stderr}")
            print("¿Tienes 'tempus-db' corriendo de docker-compose?")
            return
    except Exception as e:
        print(f"❌ Error ejecutando docker: {e}")
        return

    time.sleep(3)
    
    # ==========================================
    # ACTO 4: LA AUDITORÍA (ALERTA ROJA)
    # ==========================================
    print_step("Acto 4: Auditoría Post-Ataque (La Magia de la DDB)")
    print("⏳ Un mes después, el auditor externo revisa exactamente el mismo recibo...")
    print(f"⚖️ Verificando el recibo {receipt[:16]}...")
    
    try:
        with urllib.request.urlopen(f"{API_URL}/audit/{receipt}", timeout=5) as audit_res_2:
            audit_data_2 = json.loads(audit_res_2.read().decode('utf-8'))
            
        # Ojo que urllib arrojaría excepción si el status es 4xx, pero el endpoint de Tempus usualmente devuelve 200 con status: TAMPERED
        
        if audit_data_2.get("status") == "TAMPERED":
            print("\n[🚨] ALERTA DE SEGURIDAD ROJA: ¡MANIPULACIÓN DETECTADA!")
            print("El sello criptográfico no coincide con los datos históricos de la decisión y la llave secreta.")
            print("El motor Tempus ha impedido un fraude y ha dejado en evidencia al atacante.")
        else:
            print("❌ Algo falló. La plataforma validó la data falsa. Revisa la implementación HMAC-SHA256.")
            
    except urllib.error.HTTPError as e:
        # Algunos frameworks arrojan 400 si la validación falla. Miremos el body.
        print("\n[🚨] ALERTA DE SEGURIDAD ROJA: ¡MANIPULACIÓN DETECTADA (Rechazado por API)!")
    except Exception as e:
        print("❌ Error en la auditoría final:", e)

    print("\n🎉 Fin de la Master Demo. Tempus mantiene la verdad a salvo. 🎉\n")


if __name__ == "__main__":
    main()
