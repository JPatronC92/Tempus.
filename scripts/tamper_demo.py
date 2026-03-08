import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

# Configuración de conexión (Ajustada para correr vía Docker o localmente)
# Para correr localmente:
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "user": "postgres",
    "password": "password",
    "database": "tempus_db"
}

def tamper_latest_decision():
    print("🚀 Iniciando Operación de Manipulación (Tamper Demo)...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Buscar la última decisión
        cur.execute("SELECT id, computed_output, cryptographic_receipt FROM decision_records ORDER BY evaluated_at DESC LIMIT 1;")
        record = cur.fetchone()
        
        if not record:
            print("❌ No se encontraron registros en la Decision Database. Dispara una acción en el Explorer primero.")
            return

        print(f"🔍 Registro encontrado: ID={record['id']}")
        print(f"📦 Output Original: {json.dumps(record['computed_output'])}")
        print(f"🔒 Recibo Criptográfico: {record['cryptographic_receipt'][:12]}...")

        # 2. Manipular el output
        new_output = record['computed_output'].copy()
        if 'approved' in new_output:
            new_output['approved'] = not new_output['approved'] # Invertimos la decisión
            new_output['reason'] = "MANIPULATED_BY_HACKER"
        else:
            new_output['tampered'] = True
            new_output['reason'] = "Tampered for demo purposes"

        # 3. Guardar el cambio SIN actualizar el hash
        cur.execute(
            "UPDATE decision_records SET computed_output = %s WHERE id = %s;",
            (json.dumps(new_output), record['id'])
        )
        conn.commit()
        
        print("\n✅ ¡MANIPULACIÓN EXITOSA! ✅")
        print(f"⚠️  Nuevo Output (Manipulado): {json.dumps(new_output)}")
        print("⚠️  El recibo criptográfico NO ha sido actualizado.")
        print("\n👉 Ahora ve al Decision Explorer, selecciona este registro y pulsa 'Verify'.")
        print("👉 El sistema detectará que el contenido no coincide con el sello y se pondrá en ROJO.")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error durante la manipulación: {e}")
        print("\n💡 Tip: Asegúrate de tener 'psycopg2' instalado: pip install psycopg2-binary")

if __name__ == "__main__":
    tamper_latest_decision()
