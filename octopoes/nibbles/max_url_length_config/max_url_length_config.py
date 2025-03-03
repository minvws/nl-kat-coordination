from collections.abc import Iterator

from octopoes.models import OOI
from octopoes.models.ooi.config import Config
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.web import URL


def nibble(url: URL, config: Config) -> Iterator[OOI]:
    if "max_length" in config.config:
        max_length = int(str(config.config["max_length"]))
        if len(str(url.raw)) >= max_length:
            ft = KATFindingType(id="URL exceeds configured maximum length")
            yield ft
            yield Finding(
                finding_type=ft.reference,
                ooi=url.reference,
                proof=f"The length of {url.raw} ({len(str(url.raw))}) exceeds the configured maximum length \
({max_length}).",
            )
