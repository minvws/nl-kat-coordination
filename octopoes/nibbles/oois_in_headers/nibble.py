from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models import Reference
from octopoes.models.ooi.config import Config
from octopoes.models.ooi.network import Network
from octopoes.models.ooi.web import HTTPHeader


def query(targets: list[Reference | None]) -> str:
    sgn = "".join(str(int(isinstance(target, Reference))) for target in targets)
    if sgn == "10":
        network = str(Network(name=targets[0].split("|")[1]).reference) if targets[0] is not None else ""
        return f"""
                    {{
                        :query {{
                            :find [(pull ?header [*]) (pull ?config [*])] :where [

                                [?header :object_type "HTTPHeader"]
                                [?header :HTTPHeader/primary_key "{str(targets[0])}"]

                                (or
                                    (and
                                        [?config :Config/ooi "{network}"]
                                        [?config :Config/bit_id "oois-in-headers"]
                                    )
                                    (and
                                        [(identity nil) ?resource]
                                        [(identity nil) ?url]
                                        [(identity nil) ?network]
                                        [(identity nil) ?config]
                                    )
                                )

                            ]
                        }}
                    }}
                """
    elif sgn == "01":
        network = str(Network(name=targets[1].split("|")[1]).reference) if targets[1] is not None else ""
        return f"""
                    {{
                        :query {{
                            :find [(pull ?header [*]) (pull ?config [*])] :where [

                                [?config :object_type "Config"]
                                [?config :Config/primary_key "{str(targets[1])}"]
                                [?config :Config/bit_id "oois-in-headers"]

                                (or
                                    (and
                                        [?header :HTTPHeader/resource ?resource]
                                        [?resource :HTTPResource/web_url ?url]
                                        [?url :HostnameHTTPURL/network "{network}"]
                                    )
                                    (and
                                        [(identity nil) ?header]
                                        [(identity nil) ?resource]
                                        [(identity nil) ?url]
                                    )
                                )

                            ]
                        }}
                    }}
                """
    else:
        return f"""
                   {{
                       :query {{
                           :find [(pull ?header [*]) (pull ?config [*])] :where [
                                [?header :object_type "HTTPHeader"]
                                [?header :HTTPHeader/primary_key "{str(targets[0])}"]
                                [?config :object_type "Config"]
                                [?config :Config/primary_key "{str(targets[1])}"]
                                [?config :Config/bit_id "oois-in-headers"]
                              ]
                         }}
                    }}
                """


NIBBLE = NibbleDefinition(
    id="oois-in-headers",
    signature=[
        NibbleParameter(object_type=HTTPHeader, parser="[*][?object_type == 'HTTPHeader'][]"),
        NibbleParameter(object_type=Config, parser="[*][?object_type == 'Config'][]", optional=True),
    ],
    query=query,
)
