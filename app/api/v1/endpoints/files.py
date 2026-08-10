"""
REST API endpoints for file management operations.
"""


from fastapi import APIRouter, Depends, Query, status

from app.dependencies.deps import get_current_app, get_file_service
from app.models.app_model import App
from app.schemas.common import APIResponse, PaginatedData
from app.schemas.file_schemas import (
    ConfirmResponse,
    DownloadUrlResponse,
    FileResponse,
    UploadRequest,
    UploadUrlResponse,
)
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["Files"])


@router.post(
    "/upload-url",
    response_model=APIResponse[UploadUrlResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Request presigned S3 upload URL",
    description=(
        "**Step 1 of 3 (Request URL)**: Generates a temporary presigned S3 PUT URL (`upload_url`) "
        "and registers a `PENDING` record in the database.\n\n"
        "**Step 2 (Upload Binary to AWS S3)**: The client app/frontend issues an `HTTP PUT` request directly "
        "to the returned `upload_url` with the file binary as body (`Content-Type: <mime_type>`). "
        "*Note: This PUT request is executed directly against AWS S3, NOT against this API server.*\n\n"
        "**Step 3 (Confirm Upload)**: After AWS S3 returns HTTP 200 OK, the client calls "
        "`POST /api/v1/files/{file_uuid}/confirm` to verify S3 object existence and mark status as `COMPLETED`."
    ),
)
def get_upload_url(
    payload: UploadRequest,
    current_app: App = Depends(get_current_app),
    file_service: FileService = Depends(get_file_service),
):
    result = file_service.request_upload_url(app=current_app, payload=payload)
    return APIResponse(data=result, message="Presigned upload URL generated successfully")


@router.post(
    "/{file_uuid}/confirm",
    response_model=APIResponse[ConfirmResponse],
    summary="Confirm completed file upload",
    description="Queries AWS S3 head_object to verify existence and byte size. Transitions file status to COMPLETED.",
)
def confirm_upload(
    file_uuid: str,
    current_app: App = Depends(get_current_app),
    file_service: FileService = Depends(get_file_service),
):
    result = file_service.confirm_upload(app=current_app, file_uuid=file_uuid)
    return APIResponse(data=result, message="File upload confirmed successfully")


@router.get(
    "",
    response_model=APIResponse[PaginatedData[FileResponse]],
    summary="List files",
    description="Retrieve paginated file metadata belonging to the authenticated application.",
)
def list_files(
    owner_id: str | None = Query(None, description="Filter by end-user ID"),
    status: str | None = Query("COMPLETED", description="Filter by status: PENDING, COMPLETED, FAILED, or ALL"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_app: App = Depends(get_current_app),
    file_service: FileService = Depends(get_file_service),
):
    result = file_service.list_files(
        app=current_app,
        owner_id=owner_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    return APIResponse(data=result)


@router.get(
    "/{file_uuid}",
    response_model=APIResponse[FileResponse],
    summary="Get file metadata",
    description="Retrieve detailed metadata for a single file record by public UUID.",
)
def get_file_metadata(
    file_uuid: str,
    current_app: App = Depends(get_current_app),
    file_service: FileService = Depends(get_file_service),
):
    result = file_service.get_file(app=current_app, file_uuid=file_uuid)
    return APIResponse(data=result)


@router.get(
    "/{file_uuid}/download-url",
    response_model=APIResponse[DownloadUrlResponse],
    summary="Generate presigned S3 download URL",
    description="Generates a temporary presigned S3 GET URL with Content-Disposition headers for file download.",
)
def get_download_url(
    file_uuid: str,
    expires_in: int | None = Query(
        300, ge=60, le=86400, description="URL validity duration in seconds (min 60s, max 24 hrs)"
    ),
    current_app: App = Depends(get_current_app),
    file_service: FileService = Depends(get_file_service),
):
    result = file_service.get_download_url(app=current_app, file_uuid=file_uuid, expires_in=expires_in)
    return APIResponse(data=result, message="Presigned download URL generated successfully")


@router.delete(
    "/{file_uuid}",
    response_model=APIResponse[dict],
    summary="Delete file",
    description="Removes object from AWS S3 bucket and soft-deletes file record in database.",
)
def delete_file(
    file_uuid: str,
    current_app: App = Depends(get_current_app),
    file_service: FileService = Depends(get_file_service),
):
    file_service.delete_file(app=current_app, file_uuid=file_uuid)
    return APIResponse(data={"file_uuid": file_uuid, "deleted": True}, message="File deleted successfully")
