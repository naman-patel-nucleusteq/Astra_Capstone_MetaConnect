from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.auth import get_current_user
from app.database.database import get_db
from app.schemas.catalog_schemas import CatalogOverviewResponse, CatalogTreeResponse
from app.services import catalog_service

router = APIRouter()


@router.get("/overview", response_model=CatalogOverviewResponse)
def get_overview(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return catalog_service.get_overview(db)


@router.get("/tree", response_model=CatalogTreeResponse)
def get_tree(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return catalog_service.get_tree(db)


@router.get("/runs", response_model=list[dict])
def get_runs(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return catalog_service.get_runs(db)
