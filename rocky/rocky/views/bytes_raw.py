import json
import logging
import zipfile
from io import BytesIO
from typing import List, Dict

from django.contrib import messages
from django.http import Http404, FileResponse
from django.shortcuts import redirect
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from account.mixins import OrganizationView
from rocky.bytes_client import get_bytes_client

logger = logging.getLogger(__name__)


@class_view_decorator(otp_required)
class BytesRawView(OrganizationView):
    def get(self, request, **kwargs):
        try:
            client = get_bytes_client(self.organization.code)
            client.login()
            boefje_meta_id = kwargs["boefje_meta_id"]
            raw_metas = client.get_raw_metas(boefje_meta_id)

            raws = {raw_meta["id"]: client.get_raw(boefje_meta_id, raw_meta["id"]) for raw_meta in raw_metas}

            return FileResponse(
                zip_data(raws, raw_metas),
                filename=f"{boefje_meta_id}.zip",
            )
        except Http404 as e:
            msg = "Getting raw data failed."
            logger.error(msg)
            logger.error(e)
            messages.add_message(request, messages.ERROR, msg)

            return redirect(request.META["HTTP_REFERER"])


def zip_data(raws: Dict[str, bytes], raw_metas: List[Dict]) -> BytesIO:
    zf_buffer = BytesIO()

    with zipfile.ZipFile(zf_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for raw_meta in raw_metas:
            zf.writestr(raw_meta["id"], raws[raw_meta["id"]])
            zf.writestr(f"raw_meta_{raw_meta['id']}.json", json.dumps(raw_meta))

    zf_buffer.seek(0)

    return zf_buffer
