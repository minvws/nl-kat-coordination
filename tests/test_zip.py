import json
import zipfile
from io import BytesIO

from django.db.models import QuerySet
from django.forms import model_to_dict

from files.models import File, GenericContent
from tasks.models import TaskResult


def zip_data(raws: QuerySet) -> BytesIO:
    zf_buffer = BytesIO()

    with zipfile.ZipFile(zf_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for raw_file in raws:
            zf.writestr(str(raw_file.id), raw_file.file.read())
            zf.writestr(f"raw_meta_{raw_file.id}.json", json.dumps(model_to_dict(raw_file.task.task)))

    zf_buffer.seek(0)

    return zf_buffer


def test_zip_data(organization, task_db):
    raw1 = File.objects.create(file=GenericContent(b"1234"))
    raw2 = File.objects.create(file=GenericContent(b"4321"))
    raw3 = File.objects.create(file=GenericContent(b"asd              ss"))

    TaskResult.objects.create(task=task_db, file=raw1)
    TaskResult.objects.create(task=task_db, file=raw2)
    TaskResult.objects.create(task=task_db, file=raw3)

    raws = File.objects.all()
    z_file = zip_data(raws)
    assert zipfile.is_zipfile(z_file)

    with zipfile.ZipFile(z_file, "r") as zf:
        for raw in raws:
            raw.file.seek(0)
            assert zf.read(str(raw.id)) == raw.file.read()
