# 🚀 Manual del Propietario: Semantic Engine B2B

Este motor de búsqueda semántica de alto rendimiento ha sido diseñado para integración inmediata en entornos corporativos.

## 🏁 Inicio Rápido (1 minuto)

1.  **Configuración**:
    Copie el archivo de ejemplo:
    ```bash
    cp .env.example .env
    ```
    *(Opcional: Edite `.env` con sus propias API Keys/Secretos)*

2.  **Despliegue**:
    Levante la infraestructura completa con un solo comando:
    ```bash
    docker-compose up --build -d
    ```
    *Esto iniciará la API (Puerto 8000), Qdrant (Puerto 6333) y Redis (Puerto 6379).*

3.  **Validación**:
    Abra `http://localhost:8000/docs` en su navegador para probar la API interactiva.

## 💎 Valor del Activo

*   **Arquitectura Híbrida**: Diseñado para alta concurrencia con arquitectura asíncrona (FastAPI + AsyncIO).
*   **Persistencia Vectorial**: Qdrant configurado para almacenar datos en `docker/qdrant_data`.
*   **Seguridad B2B**: Rate Limiting (Redis) y Autenticación por API Key.
*   **Ingesta Universal**: Soporte nativo para PDF, DOCX, XLSX, CSV y TXT.
*   **Fallback Inteligente**: Si la aceleración Rust no está disponible, el sistema cambia automáticamente a modo Python optimizado.

## 🧪 Verificación de Rendimiento

El sistema incluye scripts de benchmark para validar la instalación:

```bash
# Validar concurrencia y rendimiento (RPS)
python benchmarks/benchmark_async_vs_threadpool.py

# Validar que la ingesta NO bloquea el servidor
python benchmarks/benchmark_ingest_blocking.py
```

