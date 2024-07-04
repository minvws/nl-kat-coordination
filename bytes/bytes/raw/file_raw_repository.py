import logging
from pathlib import Path
from uuid import UUID

from boto3.session import Session as BotoSession

from bytes.config import Settings
from bytes.models import BoefjeMeta, RawData
from bytes.raw.middleware import FileMiddleware, make_middleware
from bytes.repositories.raw_repository import BytesFileNotFoundException, RawRepository

logger = logging.getLogger(__name__)

BUCKETPREFIX = env.get("S3_BUCKET_PREFIX", "OpenKAT-")
BUCKET = env.get("S3_BUCKET", "OpenKAT")

def create_raw_repository(settings: Settings) -> RawRepository:
    return FileRawRepository(
        settings.data_dir,
        make_middleware(),
        folder_permissions=int(settings.folder_permission, 8),
        file_permissions=int(settings.file_permission, 8),
    )


class FileRawRepository(RawRepository):
    UUID_INDEX = 3  # To reduce the number of subdirectories based on the uuid, see self._index()

    def __init__(
        self,
        base_path: Path,
        file_middleware: FileMiddleware,
        *,
        folder_permissions: int = 0o750,
        file_permissions: int = 0o640,
    ) -> None:
        self.base_path = base_path
        self.file_middleware = file_middleware
        self._folder_permissions = folder_permissions
        self._file_permissions = file_permissions

    def save_raw(self, raw_id: UUID, raw: RawData) -> None:
        file_path = self._raw_file_path(raw_id, raw.boefje_meta)

        for parent in reversed(file_path.parents):
            parent.mkdir(exist_ok=True, mode=self._folder_permissions)

        contents = self.file_middleware.encode(raw.value)

        logger.info("Writing raw data with id %s to disk", raw_id)
        file_path.write_bytes(contents)
        file_path.chmod(self._file_permissions)

    def get_raw(self, raw_id: UUID, boefje_meta: BoefjeMeta) -> RawData:
        file_path = self._raw_file_path(raw_id, boefje_meta)

        if not file_path.exists():
            raise BytesFileNotFoundException()

        contents = file_path.read_bytes()
        return RawData(value=self.file_middleware.decode(contents), boefje_meta=boefje_meta)

    def _raw_file_path(self, raw_id: UUID, boefje_meta: BoefjeMeta) -> Path:
        return self.base_path / boefje_meta.organization / self._index(raw_id) / str(raw_id)

    def _index(self, raw_id: UUID) -> str:
        return str(raw_id)[: self.UUID_INDEX]


class S3RawRepository(RawRepository):
    def __init__(
        self,
        base_path: Str,
        file_middleware: FileMiddleware,
        access_key_id: Str,
        secret_access_key: Str,
        bucket_per_orga: Bool = True
    ) -> None:
        self.endpoint = endpoint
        self.file_middleware = file_middleware
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket_per_orga = bucket_per_orga
        self._session = None
        self._s3resource = None
    
    @property
    def s3resource(self):
        if self._s3resource:
            return self._s3resource
        self._session = BotoSession(
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key)
        self._s3resource = self._session.resource("s3")
        return self._s3resource

    def get_or_create_bucket(self, organization: Str) -> :
        bucketname = S3_BUCKET
        if self.bucket_per_orga:
            bucketname = f"{S3_BUCKET_PREFIX}{organization}"
            try:
                self.s3resource.create_bucket(Bucket=bucketname)
            except self.s3resource.meta.client.exceptions.BucketAlreadyExists
                pass # we might not be the only Bytes client trying to create this bucket
        return self.s3resource.Bucket(name=bucketname)
    
    def save_raw(self, raw_id: UUID, raw: RawData) -> None:
        file_name = self._raw_file_name(raw_id, raw.boefje_meta)
        contents = self.file_middleware.encode(raw.value)

        logger.info("Writing raw data with id %s to s3", raw_id)
        bucket = self.get_or_create_bucket(raw.boefje_meta.organization)
        bucket.Object(file_name).put(contents)

    def get_raw(self, raw_id: UUID, boefje_meta: BoefjeMeta) -> RawData:
        file_name = self._raw_file_name(raw_id, boefje_meta)
        bucket = self.get_or_create_bucket(raw.boefje_meta.organization)

        try:
            contents = bucket.Object(file_name).get()['Body'].read()
        except self.s3resource.meta.client.exceptions as error
            logger.error(f"Could not get file from s3: {bucket}/{file_name} due to {error}")
            raise BytesFileNotFoundException(error)

        return RawData(value=self.file_middleware.decode(contents), boefje_meta=boefje_meta)

    def _raw_file_name(self, raw_id: UUID, boefje_meta: BoefjeMeta) -> Str:
        if self.bucket_per_orga:
            return str(raw_id)
        return f"{boefje_meta.organization}/{raw_id}"
