"""
MetaConnect FastAPI Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.database import engine
from app.routes.connection_routes import router as connection_router
from app.routes.service_routes import router as service_router
from app.routes.metadata_routes import router as metadata_router
from app.routes.catalog_routes import router as catalog_router
from app.routes.pipeline_routes import router as pipeline_router


app = FastAPI(
    title="MetaConnect API",
    description="Lightweight data catalog and metadata management API",
    version="0.1.0"
)


# CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routers
app.include_router(
    connection_router,
    prefix="/api/connections",
    tags=["Connections"],
)

app.include_router(
    service_router,
    prefix="/api/services",
    tags=["Services"],
)

app.include_router(
    pipeline_router,
    prefix="/api",
    tags=["Pipelines"],
)

app.include_router(
    metadata_router,
    prefix="/api/metadata",
    tags=["Metadata"],
)

app.include_router(
    catalog_router,
    prefix="/api/catalog",
    tags=["Catalog"],
)



# Health endpoints
@app.get("/", tags=["Health"])
def root():
    return {"message": "MetaConnect API is running"}


@app.get("/db-health", tags=["Health"])
def database_health():
    connection = engine.connect()
    connection.close()
    return {"message": "Database connected successfully"}
