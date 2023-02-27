from datetime import timedelta, datetime
from http.cookies import SimpleCookie, CookieError
from typing import Iterator

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import Network

from octopoes.models.ooi.web import RawCookie, Cookie

from octopoes.models.ooi.findings import FindingType, Finding


def run(
    input_ooi: RawCookie,
    additional_oois,
) -> Iterator[OOI]:
    try:
        parsed_cookie = SimpleCookie(input_ooi.raw)
        for name, morsel in parsed_cookie.items():
            # https://datatracker.ietf.org/doc/html/rfc6265#section-5.3 p6
            host_only = False
            if not morsel["domain"]:
                host_only = True
                morsel["domain"] = input_ooi.response_domain.tokenized.name

            # https://datatracker.ietf.org/doc/html/rfc6265#section-5.3 p3
            persistent = False
            expires = float("inf")
            max_age = None
            if morsel["max-age"]:
                persistent = True
                try:
                    max_age = min(
                        1e8, int(morsel["max-age"])
                    )  # limit to make sure we don't trip over calculating a date millions of years in the future
                except ValueError:
                    persistent = False
                else:
                    expires = datetime.now() + timedelta(max_age)

            elif morsel["expires"]:
                persistent = True
                expires = str(datetime.strptime(morsel["expires"], "%a, %d %b %Y %H:%M:%S %Z"))

            domain = Hostname(
                name=morsel["domain"],
                network=Network(name=input_ooi.response_domain.tokenized.network.name).reference,
            )

            yield domain

            yield Cookie(
                name=name,
                value=morsel.value,
                domain=domain.reference,
                path=morsel["path"],
                secure_only=bool(morsel["secure"]),
                # https://www.rfc-editor.org/rfc/rfc6265 5.2.6
                http_only=bool(morsel["httponly"]),
                host_only=host_only,
                persistent=persistent,
                expires=expires,
                max_age=max_age,
                created=str(datetime.now()),
                same_site=morsel["samesite"],
            )
    except CookieError as e:
        ft = FindingType(id="KAT-INVALID-COOKIE")
        yield ft
        yield Finding(findings_type=ft.reference, description=f"Invalid cookie: {e}")
