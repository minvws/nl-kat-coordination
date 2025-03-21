import base64
import json
import zipfile
from io import BytesIO

import structlog
from account.mixins import OrganizationView
from django.contrib import messages
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

logger = structlog.get_logger(__name__)

RAWFILE_LIMIT = 1024 * 1024


class BytesRawView(OrganizationView):
    def get(self, request, **kwargs):
        try:
            self.bytes_client.login()
            boefje_meta_id = kwargs["boefje_meta_id"]
            raw_metas = self.bytes_client.get_raw_metas(boefje_meta_id, self.organization.code)
            if request.GET.get("format", False) == "json":
                sizelimit = request.GET.get("sizelimit", RAWFILE_LIMIT)
                for raw_meta in raw_metas:
                    raw_meta["raw_file"] = base64.b64encode(
                        self.bytes_client.get_raw(raw_meta["id"])[:sizelimit]
                    ).decode("ascii")
                return HttpResponse(json.dumps(raw_metas), content_type="application/json")
            raws = {raw_meta["id"]: self.bytes_client.get_raw(raw_meta["id"]) for raw_meta in raw_metas}
            return FileResponse(zip_data(raws, raw_metas), filename=f"{boefje_meta_id}.zip")
        except Http404 as e:
            msg = _("Getting raw data failed.")
            logger.error(msg)
            logger.error(e)

            if request.GET.get("format", False) != "json":
                messages.add_message(request, messages.ERROR, msg)

                return redirect(reverse("task_list", kwargs={"organization_code": self.organization.code}))
            return HttpResponse(json.dumps({"error": msg}), content_type="application/json", status_code=404)


def zip_data(raws: dict[str, bytes], raw_metas: list[dict]) -> BytesIO:
    zf_buffer = BytesIO()

    with zipfile.ZipFile(zf_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for raw_meta in raw_metas:
            zf.writestr(raw_meta["id"], raws[raw_meta["id"]])
            zf.writestr(f"raw_meta_{raw_meta['id']}.json", json.dumps(raw_meta))

    zf_buffer.seek(0)

    return zf_buffer
