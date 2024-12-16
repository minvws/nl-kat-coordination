from nibbles.definitions import NibbleDefinition, NibbleParameter
from octopoes.models import Reference
from octopoes.models.ooi.config import Config
from octopoes.models.ooi.web import HTTPHeaderHostname


def query(targets: list[Reference | None]) -> str:
    sgn = "".join(str(int(isinstance(target, Reference))) for target in targets)
    if sgn == "10":
        return f"""
                    {{
                        :query {{
                            :find [(pull ?header [*]) (pull ?config [*])] :where [

                                [?header :object_type "HTTPHeaderHostname"]
                                [?header :HTTPHeaderHostname/primary_key "{str(targets[0])}"]

                                (or
                                    (and
                                        [?header :HTTPHeaderHostname/hostname ?hostname]
                                        [?hostname :Hostname/network ?network]
                                        [?config :Config/ooi ?network]
                                        [?config :Config/bit_id "disallowed-csp-hostnames"]
                                    )
                                    (and
                                        [(identity nil) ?hostname]
                                        [(identity nil) ?network]
                                        [(identity nil) ?config]
                                    )
                                )

                            ]
                        }}
                    }}
                """
    elif sgn == "01":
        return f"""
                    {{
                        :query {{
                            :find [(pull ?header [*]) (pull ?config [*])] :where [

                                [?config :object_type "Config"]
                                [?config :Config/primary_key "{str(targets[1])}"]
                                [?config :Config/bit_id "disallowed-csp-hostnames"]

                                (or
                                    (and
                                        [?header :HTTPHeaderHostname/hostname ?hostname]
                                        [?hostname :Hostname/network ?network]
                                        [?config :Config/ooi ?network]
                                        [?config :Config/bit_id "disallowed-csp-hostnames"]
                                    )
                                    (and
                                        [(identity nil) ?hostname]
                                        [(identity nil) ?network]
                                        [(identity nil) ?config]
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
                                [?header :object_type "HTTPHeaderHostname"]
                                [?header :HTTPHeaderHostname/primary_key "{str(targets[0])}"]
                                [?config :object_type "Config"]
                                [?config :Config/primary_key "{str(targets[1])}"]
                                [?config :Config/bit_id "disallowed-csp-hostnames"]
                              ]
                         }}
                    }}
                """


NIBBLE = NibbleDefinition(
    id="disallowed-csp-hostnames",
    signature=[
        NibbleParameter(object_type=HTTPHeaderHostname, parser="[*][?object_type == 'HTTPHeaderHostname'][]"),
        NibbleParameter(object_type=Config, parser="[*][?object_type == 'Config'][]", optional=True),
    ],
    query=query,
)
