"""
DataStream API endpoints for ML-Auditor.
"""

from typing import List

from django.core.paginator import Paginator
from django.utils import timezone
from ninja import Router, Query
from ninja.errors import HttpError

from .models import DataStream
from .schemas import (
    DataStreamCreate,
    DataStreamFilter,
    DataStreamListResponse,
    DataStreamResponse,
)

router = Router()


@router.post("/", response=DataStreamResponse)
def create_data_stream(request, payload: DataStreamCreate):
    """Create a new data stream."""
    stream = DataStream.objects.create(
        user=request.auth,
        source_type=payload.source_type,
        payload=payload.payload,
        raw_data=payload.raw_data,
    )
    return stream


@router.get("/", response=DataStreamListResponse)
def list_data_streams(
    request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_type: str = Query(None),
    status: str = Query(None),
):
    """List data streams for current user with filtering."""
    queryset = DataStream.objects.filter(user=request.auth)

    if source_type:
        queryset = queryset.filter(source_type=source_type)
    if status:
        queryset = queryset.filter(status=status)

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    return DataStreamListResponse(
        items=list(page_obj),
        total=paginator.count,
        page=page,
        pages=paginator.num_pages,
    )


@router.get("/{stream_id}", response=DataStreamResponse)
def get_data_stream(request, stream_id: str):
    """Get data stream by ID."""
    try:
        stream = DataStream.objects.get(id=stream_id, user=request.auth)
        return stream
    except DataStream.DoesNotExist:
        raise HttpError(404, "Data stream not found")


@router.delete("/{stream_id}")
def delete_data_stream(request, stream_id: str):
    """Delete data stream."""
    try:
        stream = DataStream.objects.get(id=stream_id, user=request.auth)
        stream.delete()
        return {"success": True}
    except DataStream.DoesNotExist:
        raise HttpError(404, "Data stream not found")


@router.post("/{stream_id}/process")
def process_data_stream(request, stream_id: str):
    """Trigger processing of a data stream."""
    try:
        stream = DataStream.objects.get(id=stream_id, user=request.auth)
        if stream.status == "pending":
            stream.status = "processing"
            stream.save()
            # TODO: Trigger Celery task for processing
            return {"success": True, "message": "Processing started"}
        else:
            raise HttpError(400, "Stream already processed or processing")
    except DataStream.DoesNotExist:
        raise HttpError(404, "Data stream not found")
