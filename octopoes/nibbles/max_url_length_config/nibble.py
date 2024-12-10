from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models import Reference
from octopoes.models.ooi.config import Config
from octopoes.models.ooi.web import URL


def query(targets: list[Reference | None]) -> str:
    links = list(f'"{target}"' if isinstance(target, Reference) else "" for target in targets)
    return f"""{{
            :query {{
                :find [(pull ?var [*])]
                :where [
                    (or
                        (and [?var :object_type "URL" ] [?var :URL/primary_key {links[0]}])
                        (and [?var :object_type "Config" ] [?var :Config/primary_key {links[1]}])
                    )
                ]
            }}
        }}
        """


NIBBLE = NibbleDefinition(
    name="max_url_length_config",
    signature=[
        NibbleParameter(object_type=URL, parser="[*][?object_type == 'URL'][]"),
        NibbleParameter(object_type=Config, parser="[*][?object_type == 'Config'][]"),
    ],
    query=query,
)
