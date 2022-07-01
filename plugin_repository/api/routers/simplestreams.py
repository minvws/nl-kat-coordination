import datetime
import logging

from fastapi import APIRouter

from plugin_repository.config import PLUGINS_DIR, BASE_URL
from plugin_repository.utils.index import get_or_create_index
from plugin_repository.models import CombinedFile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/streams/v1/index.json", include_in_schema=False)
def index_file():
    index = get_or_create_index(PLUGINS_DIR)

    return {
        "index": {
            "images": {
                "datatype": "image-downloads",
                "path": "streams/v1/images.json",
                "format": "products:1.0",
                "products": [name for name in index.images.keys()],
            }
        }
    }


# todo: combined hash calc:
# todo: combined_rootxz_sha256 = sha256('lxd.tar.gz' + 'root.tar.xz')
# todo: combined_squashfs_sha256 = sha256('lxd.tar.gz' + 'root.squashfs')
# todo: combined_sha256 = combined_rootxz_sha256
# todo: https://linuxcontainers.org/lxd/docs/master/image-handling/
# todo: In this mode the image identifier is the SHA-256 of the concatenation of the metadata and rootfs tarball (in
#  that order).
@router.get("/streams/v1/images.json", include_in_schema=False)
def images_file():
    index = get_or_create_index(PLUGINS_DIR)

    response = {
        "content_id": "images",
        "datatype": "image-downloads",
        "format": "products:1.0",
        "products": {},
    }

    for product in index.images.values():
        created = datetime.datetime.strftime(
            product.plugin.created
            if product.plugin.created is not None
            else datetime.datetime.fromtimestamp(product.location.stat().st_mtime),
            "%Y%m%d_%H:%M",
        )

        versions = {created: {"items": {}}}
        for file in product.files:
            version = {
                "ftype": file.ftype,
                "size": file.size,
                "sha256": file.hash,
                "path": f"{BASE_URL}/images/{file.location.relative_to(PLUGINS_DIR)}",
            }
            if isinstance(file, CombinedFile):
                if file.combined_squashfs_sha256 is not None:
                    version["combined_squashfs_sha256"] = file.combined_squashfs_sha256
            versions[created]["items"][file.location.name] = version

        content = {
            "aliases": ",".join(product.aliases),
            # todo: What's the default architecture? The property must be set
            "arch": product.architecture or "amd64",
            "release": product.plugin.version,
            "variant": "default",
            "versions": versions,
        }

        response["products"].update({str(product): content})

    return response
