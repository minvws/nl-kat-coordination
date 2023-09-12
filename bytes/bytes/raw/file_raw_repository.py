import logging
from pathlib import Path
from uuid import UUID

from bytes.config import Settings
from bytes.models import BoefjeMeta, RawData
from bytes.raw.middleware import FileMiddleware, make_middleware
from bytes.repositories.raw_repository import BytesFileNotFoundException, RawRepository

logger = logging.getLogger(__name__)


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
