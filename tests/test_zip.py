import zipfile

from openkat.views.bytes_raw import zip_data
from tasks.models import NamedContent, RawFile, TaskResult


def test_zip_data(organization, task_db):
    raw1 = RawFile.objects.create(file=NamedContent(b"1234"))
    raw2 = RawFile.objects.create(file=NamedContent(b"4321"))
    raw3 = RawFile.objects.create(file=NamedContent(b"asd              ss"))

    TaskResult.objects.create(task=task_db, file=raw1)
    TaskResult.objects.create(task=task_db, file=raw2)
    TaskResult.objects.create(task=task_db, file=raw3)

    raws = RawFile.objects.all()
    z_file = zip_data(raws)
    assert zipfile.is_zipfile(z_file)

    with zipfile.ZipFile(z_file, "r") as zf:
        for raw in raws:
            raw.file.seek(0)
            assert zf.read(str(raw.id)) == raw.file.read()
