import abc
import base64

from nacl.public import PrivateKey, PublicKey, Box

from katalogus.models import Base64Str


class EncryptMiddleware(abc.ABC):
    @abc.abstractmethod
    def encode(self, contents: str) -> str:
        pass

    @abc.abstractmethod
    def decode(self, contents: str) -> str:
        pass


class IdentityMiddleware(EncryptMiddleware):
    def encode(self, contents: str) -> str:
        return contents

    def decode(self, contents: str) -> str:
        return contents


class NaclBoxMiddleware(EncryptMiddleware):
    """NaclBoxMiddleware implements NaCl Box encryption
    More info: https://pynacl.readthedocs.io/en/latest/public/
    """

    def __init__(self, private_key: Base64Str, public_key: Base64Str):
        sk = PrivateKey(base64.b64decode(private_key))
        pk = PublicKey(base64.b64decode(public_key))
        self.box: Box = Box(sk, pk)

    def encode(self, contents: str) -> str:
        encrypted_contents = self.box.encrypt(contents.encode())
        encrypted_contents = base64.b64encode(encrypted_contents)
        return encrypted_contents.decode()

    def decode(self, contents: str) -> str:
        encrypted_binary = base64.b64decode(contents)
        nonce = encrypted_binary[0 : self.box.NONCE_SIZE]
        data = encrypted_binary[self.box.NONCE_SIZE :]

        return self.box.decrypt(data, nonce).decode()
