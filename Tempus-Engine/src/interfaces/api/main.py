from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import get_settings
from src.interfaces.api.routers.v1 import billing, rules, govern

settings = get_settings()

app = FastAPI(
    title="Tempus Billing API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(billing.router, prefix=f"{settings.API_V1_STR}/billing", tags=["billing"])
app.include_router(rules.router, prefix=f"{settings.API_V1_STR}/rules", tags=["rules"])
app.include_router(govern.router, prefix=f"{settings.API_V1_STR}/govern", tags=["governance"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Tempus Billing & Commission Engine API"}
