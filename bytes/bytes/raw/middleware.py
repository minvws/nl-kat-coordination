import base64

from nacl.public import Box, PrivateKey, PublicKey

from bytes.config import get_settings
from bytes.models import EncryptionMiddleware


class FileMiddleware:
    def encode(self, contents: bytes) -> bytes:
        raise NotImplementedError()

    def decode(self, contents: bytes) -> bytes:
        raise NotImplementedError()


def make_middleware() -> FileMiddleware:
    settings = get_settings()

    if settings.encryption_middleware == EncryptionMiddleware.NACL_SEALBOX:
        return NaclBoxMiddleware(settings.private_key_b64, settings.public_key_b64)

    return IdentityMiddleware()


class IdentityMiddleware(FileMiddleware):
    def encode(self, contents: bytes) -> bytes:
        return contents

    def decode(self, contents: bytes) -> bytes:
        return contents


class NaclBoxMiddleware(FileMiddleware):
    def __init__(self, kat_private: str, vws_public: str):
        private_key = PrivateKey(base64.b64decode(kat_private))
        public_key = PublicKey(base64.b64decode(vws_public))
        self.box: Box = Box(private_key, public_key)

    def encode(self, contents: bytes) -> bytes:
        return self.box.encrypt(contents)

    def decode(self, contents: bytes) -> bytes:
        nonce = contents[0 : self.box.NONCE_SIZE]
        data = contents[self.box.NONCE_SIZE :]

        return self.box.decrypt(data, nonce)
