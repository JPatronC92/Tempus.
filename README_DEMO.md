# 🎙️ Decision Database: The "Brutal" Demo Script

Este documento es el guion paso a paso para realizar una presentación de alto impacto de la **Decision Database (DDB)** ante inversores o clientes.

---

## 0. Preparación (The Setup)
1.  Asegúrate de que el sistema esté corriendo: `docker compose up -d`.
2.  Abre el navegador en: `http://localhost:3000/explorer`.
3.  (Opcional) Abre la base de datos en una terminal para mostrar que "debajo" hay SQL real: `docker exec -it tempus-db psql -U postgres -d tempus`.

---

## 1. El Gancho (The Hook)
> "Hoy en día, las empresas tienen miedo de la IA porque es una 'Caja Negra'. Los agentes alucinan. El software tradicional no debería. 
> 
> Presentamos **Tempus**: El registrador de vuelo para Agentes de IA. No guardamos solo datos, guardamos **por qué** un sistema actuó."

---

## 2. La Acción en Vivo (The Live Feed)
**Acción:** Señala el "Global Decision Timeline".
> "Aquí vemos el pulso de la empresa. Cada vez que un Agente Autónomo (Alpha-Agent, Compliance-Bot) intenta hacer algo, pasa por nuestro filtro de gobernanza en Rust."

**Acción:** Pulsa el botón **⚡ Trigger Agent Action** un par de veces.
> "Miren esto. En milisegundos, el agente propone, Tempus valida contra reglas deterministas y sella la decisión. No hay dudas, no hay alucinaciones."

---

## 3. La Anatomía de una Decisión (The Causal Trace)
**Acción:** Haz clic en una de las decisiones del timeline (preferiblemente una que diga `BLOCKED`).
> "Si un regulador o un cliente pregunta: '¿Por qué me denegaron este crédito?', ya no respondemos 'El modelo de IA dijo que no'. 
> 
> Aquí tenemos la **Traza Causal**. Vemos exactamente qué agente lo pidió, qué versión de la regla se aplicó, qué contexto recuperó de los documentos y cuál fue el output exacto. Es trazabilidad total."

---

## 4. La Inmutabilidad (The Trust Test)
**Acción:** Pulsa el botón **"Verify Cryptographic Signature"**.
> "Cada decisión genera un **Recibo Criptográfico** (HMAC-SHA256). Este hash es el sello de garantía. Si alguien intenta entrar en la base de datos y cambiar un 'APPROVED' por un 'REJECTED' para cometer fraude, el sistema de auditoría lo detectará al instante."

*(Aquí es donde haríamos la Tamper Demo si está lista)*.

---

## 5. El Cierre (The Closing)
> "Esto es la Decision Database. La infraestructura necesaria para que la IA pase de ser un juguete de chat a una herramienta corporativa confiable. 
> 
> **AI models hallucinate. Software shouldn't. Welcome to the era of Governance.**"
