from unittest import TestCase

from boefjes.job_models import NormalizerMeta
from boefjes.plugins.kat_security_txt_downloader.normalize import run
from tests.stubs import get_dummy_data


class SecurityTXTTest(TestCase):
    maxDiff = None

    def test_security_txt_same_website(self):
        meta = NormalizerMeta.parse_raw(get_dummy_data("security-txt-normalizer.json"))

        oois = list(
            run(
                meta,
                get_dummy_data("inputs/security_txt_result_same_website.json"),
            )
        )

        expected = (
            "[URL(object_type='URL', scan_profile=None, "
            "primary_key='URL|internet|https://example.nl/.well-known/security.txt', "
            "network=Reference('Network|internet'), raw=AnyUrl('https://example.nl/.well-known/security.txt', "
            "scheme='https', host='example.nl', tld='nl', host_type='domain', "
            "path='/.well-known/security.txt'), web_url=None), URL(object_type='URL', "
            "scan_profile=None, primary_key='URL|internet|https://example.nl/.well-known/security.txt', "
            "network=Reference('Network|internet'), raw=AnyUrl('https://example.nl/.well-known/security.txt', "
            "scheme='https', host='example.nl', tld='nl', host_type='domain', "
            "path='/.well-known/security.txt'), web_url=None), SecurityTXT(object_type='SecurityTXT', "
            "scan_profile=None, primary_key='SecurityTXT|internet|8.8.8.8|tcp|443|https|internet|example.nl|"
            "internet|https://example.nl/.well-known/security.txt', website=Reference('Website|"
            "internet|8.8.8.8|tcp|443|https|internet|example.nl'), "
            "url=Reference('URL|internet|https://example.nl/.well-known/security.txt'), "
            "redirects_to=None, security_txt='This is the content')]"
        )

        self.assertEqual(expected, str(oois))

    def test_security_txt_different_website(self):
        meta = NormalizerMeta.parse_raw(get_dummy_data("security-txt-normalizer.json"))

        oois = list(
            run(
                meta,
                get_dummy_data("inputs/security_txt_result_different_website.json"),
            )
        )

        expected = (
            "[URL(object_type='URL', scan_profile=None, "
            "primary_key='URL|internet|https://example.nl/.well-known/security.txt', "
            "network=Reference('Network|internet'), raw=AnyUrl('https://example.nl/.well-known/security.txt', "
            "scheme='https', host='example.nl', tld='nl', host_type='domain', "
            "path='/.well-known/security.txt'), web_url=None), URL(object_type='URL', scan_profile=None, "
            "primary_key='URL|internet|https://www.example.nl/.well-known/security.txt', "
            "network=Reference('Network|internet'), "
            "raw=AnyUrl('https://www.example.nl/.well-known/security.txt', "
            "scheme='https', host='www.example.nl', tld='nl', host_type='domain', "
            "path='/.well-known/security.txt'), web_url=None), Hostname(object_type='Hostname', "
            "scan_profile=None, primary_key='Hostname|internet|www.example.nl', "
            "network=Reference('Network|internet'), name='www.example.nl', dns_zone=None, "
            "registered_domain=None), IPAddressV4(object_type='IPAddressV4', scan_profile=None, "
            "primary_key='IPAddressV4|internet|1.8.8.8', address=IPv4Address('1.8.8.8'), "
            "network=Reference('Network|internet'), netblock=None), Service(object_type='Service', "
            "scan_profile=None, primary_key='Service|https', name='https'), IPPort(object_type='IPPort', "
            "scan_profile=None, primary_key='IPPort|internet|1.8.8.8|tcp|443', "
            "address=Reference('IPAddressV4|internet|1.8.8.8'), protocol=<Protocol.TCP: 'tcp'>, port=443, "
            "state=None), IPService(object_type='IPService', scan_profile=None, "
            "primary_key='IPService|internet|1.8.8.8|tcp|443|https', "
            "ip_port=Reference('IPPort|internet|1.8.8.8|tcp|443'), service=Reference('Service|https')), "
            "Website(object_type='Website', scan_profile=None, "
            "primary_key='Website|internet|1.8.8.8|tcp|443|https|internet|www.example.nl', "
            "ip_service=Reference('IPService|internet|1.8.8.8|tcp|443|https'), "
            "hostname=Reference('Hostname|internet|www.example.nl'), certificate=None), "
            "SecurityTXT(object_type='SecurityTXT', scan_profile=None, "
            "primary_key='SecurityTXT|internet|1.8.8.8|tcp|443|https|internet|www.example.nl|internet|"
            "https://www.example.nl/.well-known/security.txt', "
            "website=Reference('Website|internet|1.8.8.8|tcp|443|https|internet|www.example.nl'), "
            "url=Reference('URL|internet|https://www.example.nl/.well-known/security.txt'), "
            "redirects_to=None, security_txt='This is the content'), SecurityTXT(object_type='SecurityTXT', "
            "scan_profile=None, primary_key='SecurityTXT|internet|8.8.8.8|tcp|443|https|internet|example.nl|"
            "internet|https://example.nl/.well-known/security.txt', "
            "website=Reference('Website|internet|8.8.8.8|tcp|443|https|internet|example.nl'), "
            "url=Reference('URL|internet|https://example.nl/.well-known/security.txt'), "
            "redirects_to=Reference('SecurityTXT|internet|1.8.8.8|tcp|443|https|internet|www.example.nl|"
            "internet|https://www.example.nl/.well-known/security.txt'), security_txt=None)]"
        )

        self.assertEqual(expected, str(oois))
