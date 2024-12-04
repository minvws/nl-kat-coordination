from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models.ooi.config import Config
from octopoes.models.ooi.web import URL

NIBBLE = NibbleDefinition(
    name="max_url_length_config",
    signature=[
        NibbleParameter(object_type=URL, parser="[*][?object_type == 'URL'][]"),
        NibbleParameter(object_type=Config, parser="[*][?object_type == 'Config'][]"),
    ],
    query="""
    {
        :query {
            :find [(pull ?var [*])]
            :where [
                (or
                    (and [?var :object_type "URL" ] [?var :URL/primary_key $1])
                    (and [?var :object_type "Config" ] [?var :Config/primary_key $2])
                )
            ]
        }
    }
    """,
    min_scan_level=-1,
)
