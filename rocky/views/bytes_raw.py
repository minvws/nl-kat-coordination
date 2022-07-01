import json
import logging
import zipfile
from io import BytesIO

from django.contrib import messages
from django.http import Http404, FileResponse
from django.shortcuts import redirect
from django.views import View
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from rocky.bytes_client import get_bytes_client

logger = logging.getLogger(__name__)


@class_view_decorator(otp_required)
class BytesRawView(View):
    def get(self, request, boefje_meta_id: str):
        try:
            client = get_bytes_client()
            client.login()
            raw = client.get_raw(boefje_meta_id)
            boefje_meta = client.get_raw_meta(boefje_meta_id)

            return FileResponse(
                zip_data(raw, boefje_meta_id, boefje_meta),
                filename=f"{boefje_meta_id}.zip",
            )
        except Http404 as e:
            msg = "Getting raw data failed."
            logger.error(msg)
            logger.error(e)
            messages.add_message(request, messages.ERROR, msg)

            return redirect(request.META["HTTP_REFERER"])


def zip_data(data: bytes, boefje_meta_id: str, boefje_meta: dict) -> BytesIO:
    zf_buffer = BytesIO()

    with zipfile.ZipFile(zf_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(boefje_meta_id, data)
        zf.writestr("raw_meta.json", json.dumps(boefje_meta))

    zf_buffer.seek(0)

    return zf_buffer
