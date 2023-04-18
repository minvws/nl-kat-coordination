from typing import List

from bytes.models import BoefjeMeta, RawData


class BytesFileNotFoundException(FileNotFoundError):
    """Exception for when no requested Bytes file was found."""


class RawRepository:
    def save_raw(self, raw_id: str, raw: RawData) -> None:
        raise NotImplementedError()

    def get_raw(self, raw_id: str, boefje_meta: BoefjeMeta) -> RawData:
        raise NotImplementedError()

    def get_raw_file_count(self, organization_id: str) -> int:
        raise NotImplementedError()

    def get_organizations(self) -> List[str]:
        raise NotImplementedError()
