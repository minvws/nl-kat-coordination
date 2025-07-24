import zipfile

from files.models import File, GenericContent
from openkat.views.bytes_raw import zip_data
from tasks.models import TaskResult


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
