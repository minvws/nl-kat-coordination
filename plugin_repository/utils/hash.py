import logging
import subprocess
from pathlib import Path
from typing import List, Optional

import diskcache

from plugin_repository.models import File, CombinedFile

logger = logging.getLogger(__name__)


class Hasher:
    def __init__(self, cache: diskcache.Cache):
        self.cache = cache

    @staticmethod
    def generate_hash(file: Path) -> str:
        result = subprocess.run(
            ["shasum", "--algorithm", "256", file.as_posix()], stdout=subprocess.PIPE
        )

        return result.stdout.decode().split()[0]

    def get_or_generate_hash(self, file: Path) -> str:
        key = file, file.stat().st_mtime

        if key not in self.cache:
            logger.warning('cache miss for "%s"', file)
            hashed = self.generate_hash(file)
            self.cache[key] = hashed
            logger.info("generated %s", hashed)
        else:
            logger.info('cache hit for "%s"', file)
            hashed = self.cache[key]

        return hashed

    @staticmethod
    def generate_combined_hash(metadata: Path, rootfs: Path) -> str:
        process = subprocess.Popen(
            ["cat", metadata.as_posix(), rootfs.as_posix()], stdout=subprocess.PIPE
        )
        output = subprocess.check_output(
            ["shasum", "--algorithm", "256"], stdin=process.stdout
        )

        process.wait()

        return output.decode().split()[0]

    def get_or_generate_combined_hash(self, metadata: Path, rootfs: Path) -> str:
        key = (
            metadata,
            metadata.stat().st_mtime,
            rootfs,
            rootfs.stat().st_mtime,
        )

        if key not in self.cache:
            logger.warning('cache miss for "%s" and "%s"', metadata, rootfs)
            hashed = self.generate_combined_hash(metadata, rootfs)
            self.cache[key] = hashed
            logger.info("generated %s", hashed)
        else:
            logger.info('cache hit for "%s" and "%s"', metadata, rootfs)
            hashed = self.cache[key]

        return hashed

    def generate_hashes(self, files: List[File]) -> None:
        for file in files:
            hashed = self.get_or_generate_hash(file.location)
            file.hash = hashed

            if isinstance(file, CombinedFile):
                metadata = file.location
                rootfs_squash = _find_ftype("squashfs", files)
                if rootfs_squash is not None and rootfs_squash.location.exists():
                    file.combined_squashfs_sha256 = self.get_or_generate_combined_hash(
                        metadata, rootfs_squash.location
                    )
                rootfs_xz = _find_ftype("root.tar.xz", files)
                if rootfs_xz is not None and rootfs_xz.location.exists():
                    file.combined_rootxz_sha256 = self.get_or_generate_combined_hash(
                        metadata, rootfs_xz.location
                    )
                rootfs_disk_vm_img = _find_ftype("disk-kvm.img", files)
                if (
                    rootfs_disk_vm_img is not None
                    and rootfs_disk_vm_img.location.exists()
                ):
                    file.combined_disk_vm_img_sha256 = (
                        self.get_or_generate_combined_hash(
                            metadata, rootfs_disk_vm_img.location
                        )
                    )


def _find_ftype(ftype: str, files: List[File]) -> Optional[File]:
    try:
        return next(filter(lambda f: f.ftype == ftype, files))
    except StopIteration:
        return None
