import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from starlette.responses import JSONResponse

from bytes.api.models import RawResponse
from bytes.auth import authenticate_token
from bytes.database.sql_meta_repository import MetaIntegrityError, ObjectNotFoundException, create_meta_data_repository
from bytes.events.events import RawFileReceived
from bytes.events.manager import EventManager
from bytes.models import BoefjeMeta, MimeType, NormalizerMeta, RawData, RawDataMeta
from bytes.rabbitmq import create_event_manager
from bytes.repositories.meta_repository import BoefjeMetaFilter, MetaDataRepository, NormalizerMetaFilter, RawDataFilter

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(authenticate_token)])
BOEFJE_META_TAG = "BoefjeMeta"
NORMALIZER_META_TAG = "NormalizerMeta"
RAW_TAG = "Raw"


@router.post("/boefje_meta", tags=[BOEFJE_META_TAG])
def create_boefje_meta(
    boefje_meta: BoefjeMeta,
    meta_repository: MetaDataRepository = Depends(create_meta_data_repository),
) -> JSONResponse:
    try:
        with meta_repository:
            meta_repository.save_boefje_meta(boefje_meta)
    except MetaIntegrityError:
        return JSONResponse(
            {"status": "failed", "message": "Integrity error: object might already exist"}, status_code=400
        )

    return JSONResponse({"status": "success"}, status_code=201)


@router.get("/boefje_meta/{boefje_meta_id}", response_model=BoefjeMeta, tags=[BOEFJE_META_TAG])
def get_boefje_meta_by_id(
    boefje_meta_id: UUID,
    meta_repository: MetaDataRepository = Depends(create_meta_data_repository),
) -> BoefjeMeta:
    with meta_repository:
        meta = meta_repository.get_boefje_meta_by_id(boefje_meta_id)
        logger.debug("Found meta: %s", meta)

        return meta


@router.get("/boefje_meta", response_model=List[BoefjeMeta], tags=[BOEFJE_META_TAG])
def get_boefje_meta(
    organization: str,
    boefje_id: Optional[str] = None,
    input_ooi: Optional[str] = None,
    limit: int = 1,
    offset: int = 0,
    descending: bool = True,
    meta_repository: MetaDataRepository = Depends(create_meta_data_repository),
) -> List[BoefjeMeta]:
    logger.debug(
        "Filtering boefje_meta on: boefje_id=%s, input_ooi=%s, limit=%s, descending=%s",
        boefje_id,
        input_ooi,
        limit,
        descending,
    )
    query_filter = BoefjeMetaFilter(
        organization=organization,
        boefje_id=boefje_id,
        input_ooi=input_ooi,
        limit=limit,
        offset=offset,
        descending=descending,
    )

    with meta_repository:
        boefje_meta_list = meta_repository.get_boefje_meta(query_filter)

    logger.debug("Found %s boefje meta entries", len(boefje_meta_list))
    return boefje_meta_list


@router.post("/normalizer_meta", tags=[NORMALIZER_META_TAG])
def create_normalizer_meta(
    normalizer_meta: NormalizerMeta,
    meta_repository: MetaDataRepository = Depends(create_meta_data_repository),
) -> JSONResponse:
    try:
        with meta_repository:
            meta_repository.save_normalizer_meta(normalizer_meta)
    except MetaIntegrityError:
        return JSONResponse(
            {"status": "failed", "message": "Integrity error: object might already exist"}, status_code=400
        )

    return JSONResponse({"status": "success"}, status_code=201)


@router.get("/normalizer_meta/{normalizer_meta_id}", response_model=NormalizerMeta, tags=[NORMALIZER_META_TAG])
def get_normalizer_meta_by_id(
    normalizer_meta_id: UUID,
    meta_repository: MetaDataRepository = Depends(create_meta_data_repository),
) -> NormalizerMeta:
    with meta_repository:
        return meta_repository.get_normalizer_meta_by_id(normalizer_meta_id)


@router.get("/normalizer_meta", response_model=List[NormalizerMeta], tags=[NORMALIZER_META_TAG])
def get_normalizer_meta(
    organization: str,
    normalizer_id: Optional[str] = None,
    raw_id: Optional[UUID] = None,
    limit: int = 1,
    offset: int = 0,
    descending: bool = True,
    meta_repository: MetaDataRepository = Depends(create_meta_data_repository),
) -> List[NormalizerMeta]:
    logger.debug(
        "Filtering normalizer_meta on: normalizer_id=%s, raw_id=%s, limit=%s, offset=%s, descending=%s",
        normalizer_id,
        raw_id,
        limit,
        offset,
        descending,
    )
    query_filter = NormalizerMetaFilter(
        organization=organization,
        normalizer_id=normalizer_id,
        raw_id=raw_id,
        limit=limit,
        offset=offset,
        descending=descending,
    )

    with meta_repository:
        normalizer_meta_list = meta_repository.get_normalizer_meta(query_filter)

    logger.debug("Found %s normalizer meta entries", len(normalizer_meta_list))
    return normalizer_meta_list


@router.post("/raw", tags=[RAW_TAG])
async def create_raw(
    request: Request,
    boefje_meta_id: UUID,
    mime_types: Optional[List[str]] = Query(None),
    meta_repository: MetaDataRepository = Depends(create_meta_data_repository),
    event_manager: EventManager = Depends(create_event_manager),
) -> RawResponse:
    parsed_mime_types = [] if mime_types is None else [MimeType(value=mime_type) for mime_type in mime_types]

    try:
        meta = meta_repository.get_boefje_meta_by_id(boefje_meta_id)

        if meta_repository.has_raw(meta, parsed_mime_types):
            return RawResponse(status="success", message="Raw data already present")

        data = await request.body()

        raw_data = RawData(value=data, boefje_meta=meta, mime_types=parsed_mime_types)
        with meta_repository:
            raw_id = meta_repository.save_raw(raw_data)

        event = RawFileReceived(
            organization=meta.organization,
            raw_data=RawDataMeta(
                id=raw_id,
                boefje_meta=raw_data.boefje_meta,
                mime_types=raw_data.mime_types,
            ),
        )
        event_manager.publish(event)
    except Exception as error:
        logger.exception("Error saving raw data")
        raise HTTPException(status_code=500, detail="Could not save raw data") from error

    return RawResponse(status="success", message="Raw data saved", id=raw_id)


@router.get("/raw/{raw_id}", tags=[RAW_TAG])
def get_raw_by_id(
    raw_id: UUID,
    meta_repository: MetaDataRepository = Depends(create_meta_data_repository),
) -> Response:
    try:
        raw_data = meta_repository.get_raw_by_id(raw_id)
    except ObjectNotFoundException as error:
        raise HTTPException(status_code=404, detail="No raw data found") from error

    return Response(raw_data.value, media_type="application/octet-stream")


@router.get("/raw", response_model=List[RawDataMeta], tags=[RAW_TAG])
def get_raws(
    organization: Optional[str] = None,
    boefje_meta_id: Optional[UUID] = None,
    normalized: Optional[bool] = None,
    limit: int = 1,
    mime_types: Optional[List[str]] = Query(None),
    meta_repository: MetaDataRepository = Depends(create_meta_data_repository),
) -> List[RawDataMeta]:
    """Get a filtered list of RawDataMeta objects, which contains metadata of a RawData object without the contents"""

    parsed_mime_types = [] if mime_types is None else [MimeType(value=mime_type) for mime_type in mime_types]

    query_filter = RawDataFilter(
        organization=organization,
        boefje_meta_id=boefje_meta_id,
        normalized=normalized,
        mime_types=parsed_mime_types,
        limit=limit,
    )

    logger.info("mime_types: %s", parsed_mime_types)

    return meta_repository.get_raw(query_filter)
