import urllib.request
import json
import time
import subprocess

# Configuración
API_URL = "http://localhost:8001/api/v1/govern"

def print_step(title):
    print(f"\n{'='*60}")
    print(f"{title.upper()}")
    print(f"{'='*60}")

def main():
    print_step("Paso 1: Generando una Decisión (El Agente Actúa)")
    
    payload = {
        "agent_id": "loan-assessor-ai",
        "rule_name": "credit_policy_v1",
        "context": {"doc": "user_profile_123"},
        "input_data": {"credit_score": 750, "amount": 50000}
    }
    
    data_json = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(f"{API_URL}/decide", data=data_json, headers={'Content-Type': 'application/json'})
    
    print(f"Enviando solicitud al motor Tempus: {payload}")
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            data = json.loads(res_body)
    except Exception as e:
        print("Error al generar decisión:", e)
        return
        
    receipt = data.get("receipt")
    decision = data.get("decision")
    
    print(f"\n[+] Decisión Tomada: {decision}")
    print(f"[+] Sello Criptográfico: {receipt}")
    time.sleep(2)
    
    print_step("Paso 2: Auditoría Normal (El Tribunal Revisa)")
    print(f"Verificando el recibo {receipt[:12]}...")
    
    try:
        with urllib.request.urlopen(f"{API_URL}/audit/{receipt}") as audit_res:
            audit_data = json.loads(audit_res.read().decode('utf-8'))
    except Exception as e:
        print("Error en auditoría:", e)
        return
    
    if audit_data.get("status") == "VALID":
        print("\n[✓] Auditoría Exitosa: El registro es íntegro y no ha sido alterado.")
    else:
        print("\n[✗] Fallo en la auditoría inicial")
        
    time.sleep(3)
    
    print_step("Paso 3: El Ataque (Simulando un DBA corrupto)")
    print("Conectando directamente a la base de datos PostgreSQL mediante Docker...")
    print("Un hacker o administrador intenta cambiar el resultado de 'approved: True' a 'false' sin dejar rastro.\n")
    
    hacked_output = '{"reason": "corrupted", "approved": false}'
    
    # We use docker exec to run the psql command directly, no psycopg2 needed.
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
        if result.returncode == 0:
            print(f"[!] INTRUSIÓN EXITOSA: Fila modificada en PostgreSQL directamente por SQL.")
        else:
            print(f"Error modificando DB: {result.stderr}")
            return
    except Exception as e:
        print(f"Error ejecutando docker: {e}")
        return

    time.sleep(3)
    
    print_step("Paso 4: Auditoría Post-Ataque (La Magia de la DDB)")
    print("Un mes después, el auditor o el juez revisa exactamente el mismo recibo.")
    print(f"Verificando el recibo {receipt[:12]}...")
    
    try:
        with urllib.request.urlopen(f"{API_URL}/audit/{receipt}") as audit_res_2:
            audit_data_2 = json.loads(audit_res_2.read().decode('utf-8'))
        
        if audit_data_2.get("status") == "TAMPERED":
            print("\n[🚨] ALERTA DE SEGURIDAD ROJA: ¡MANIPULACIÓN DETECTADA!")
            print("El sello criptográfico no coincide con los datos históricos de la decisión.")
            print("El motor de gobernanza ha impedido un fraude y ha dejado en evidencia al atacante.")
        else:
            print("Algo falló. La plataforma no detectó el ataque.")
            
    except Exception as e:
        print("Error en la auditoría final:", e)

if __name__ == "__main__":
    main()
