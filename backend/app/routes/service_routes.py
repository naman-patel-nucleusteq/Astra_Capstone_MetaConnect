"""
Service CRUD and ingestion endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.schemas.service_schemas import ConnectorCapabilities, ServiceConnectionTest, ServiceCreate, ServiceResponse, ServiceUpdate
from app.schemas.ingestion_schemas import IngestionRunResponse, IngestionTriggerResponse
from app.core.auth import get_current_user
from app.services import source_service


router = APIRouter()


def service_response(service) -> ServiceResponse:
    response = ServiceResponse.model_validate(service)
    response.capabilities = ConnectorCapabilities(**source_service.service_capabilities(service))
    return response


@router.get("", response_model=list[ServiceResponse])
def get_all_services(db: Session = Depends(get_db), current_user: str = Depends(get_current_user),):
    """
    Return all registered services
    """
    return [service_response(service) for service in source_service.list_services(db)]


@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(
    service: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Create a new data-source service and persist it to the catalog DB
    """

    return service_response(source_service.create_service(service, db, current_user))


@router.get("/{service_uuid}", response_model=ServiceResponse)
def get_service(service_uuid: UUID, db: Session = Depends(get_db), current_user: str = Depends(get_current_user),):
    """
    Return a single service by its UUID
    """

    return service_response(source_service.get_service(service_uuid, db))


@router.put("/{service_uuid}", response_model=ServiceResponse)
def update_service(
    service_uuid: UUID,
    payload: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return service_response(source_service.update_service(service_uuid, payload, db))


@router.post("/{service_uuid}/test", response_model=dict)
def test_updated_service(
    service_uuid: UUID,
    payload: ServiceConnectionTest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return source_service.test_updated_service_connection(service_uuid, payload, db)


@router.delete("/{service_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Delete a service by its UUID
    """
    source_service.delete_service(service_uuid, db)

