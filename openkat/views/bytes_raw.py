import json
import zipfile
from io import BytesIO

import structlog
from django.db.models import QuerySet
from django.forms import model_to_dict
from django.http import FileResponse

from account.mixins import OrganizationView
from tasks.models import RawFile

logger = structlog.get_logger(__name__)


class BytesRawView(OrganizationView):
    def get(self, request, **kwargs):
        boefje_meta_id = kwargs["boefje_meta_id"]
        raws = RawFile.objects.filter(task__task__id=boefje_meta_id, task__task__organization=self.organization)

        return FileResponse(zip_data(raws), filename=f"{boefje_meta_id}.zip")


def zip_data(raws: QuerySet) -> BytesIO:
    zf_buffer = BytesIO()

    with zipfile.ZipFile(zf_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for raw_file in raws:
            zf.writestr(str(raw_file.id), raw_file.file.read())
            zf.writestr(f"raw_meta_{raw_file.id}.json", json.dumps(model_to_dict(raw_file.task.task)))

    zf_buffer.seek(0)

    return zf_buffer
