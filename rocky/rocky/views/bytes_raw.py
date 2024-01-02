import json
import logging
import zipfile
from io import BytesIO
from typing import Dict, List

from account.mixins import OrganizationView
from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class BytesRawView(OrganizationView):
    def get(self, request, **kwargs):
        try:
            self.bytes_client.login()
            boefje_meta_id = kwargs["boefje_meta_id"]
            raw_metas = self.bytes_client.get_raw_metas(boefje_meta_id, self.organization.code)
            raws = {raw_meta["id"]: self.bytes_client.get_raw(raw_meta["id"]) for raw_meta in raw_metas}

            return FileResponse(
                zip_data(raws, raw_metas),
                filename=f"{boefje_meta_id}.zip",
            )
        except Http404 as e:
            msg = _("Getting raw data failed.")
            logger.error(msg)
            logger.error(e)
            messages.add_message(request, messages.ERROR, msg)
            return redirect(reverse("task_list", kwargs={"organization_code": self.organization.code}))


def zip_data(raws: Dict[str, bytes], raw_metas: List[Dict]) -> BytesIO:
    zf_buffer = BytesIO()

    with zipfile.ZipFile(zf_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for raw_meta in raw_metas:
            zf.writestr(raw_meta["id"], raws[raw_meta["id"]])
            zf.writestr(f"raw_meta_{raw_meta['id']}.json", json.dumps(raw_meta))

    zf_buffer.seek(0)

    return zf_buffer
