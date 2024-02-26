import base64
from unittest import TestCase

from nacl.public import PrivateKey

from boefjes.katalogus.dependencies.encryption import NaclBoxMiddleware


class TestSettingsEncryption(TestCase):
    def setUp(self) -> None:
        sk = PrivateKey.generate()
        sk_b64 = base64.b64encode(bytes(sk)).decode()
        pub_b64 = base64.b64encode(bytes(sk.public_key)).decode()
        self.encryption = NaclBoxMiddleware(private_key=sk_b64, public_key=pub_b64)

    def test_encode_decode(self):
        msg = "The president is taking the underpass"

        encrypted = self.encryption.encode(msg)
        decrypted = self.encryption.decode(encrypted)

        self.assertNotEqual(encrypted, msg)
        self.assertEqual(msg, decrypted)
