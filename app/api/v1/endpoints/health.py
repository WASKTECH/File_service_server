"""
Health check endpoints for container orchestrators (Kubernetes / AWS ECS).
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db_session
from app.services.s3_service import S3Service
from app.dependencies.deps import get_s3_service
from app.schemas.common import APIResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=APIResponse[dict],
    summary="Health check probe",
    description="Evaluates operational health of database connection and AWS S3 integration.",
)
def health_check(
    db: Session = Depends(get_db_session),
    s3_service: S3Service = Depends(get_s3_service),
):
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    s3_status = "healthy"
    try:
        # Fast test presigned URL generation to verify credentials/region
        s3_service.generate_presigned_download_url("health_test_key", "test.txt", expires_in=60)
    except Exception as e:
        s3_status = f"unhealthy: {str(e)}"

    overall_healthy = db_status == "healthy" and s3_status == "healthy"

    return APIResponse(
        success=overall_healthy,
        data={
            "status": "UP" if overall_healthy else "DOWN",
            "database": db_status,
            "s3_storage": s3_status,
        },
        message="System health check completed",
    )
