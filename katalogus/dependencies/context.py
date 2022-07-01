from pydantic import BaseSettings, BaseModel

from katalogus.models import EncryptionMiddleware


class Environment(BaseSettings):
    encryption_middleware: EncryptionMiddleware = EncryptionMiddleware.IDENTITY
    katalogus_private_key_b64: str = ""
    katalogus_public_key_b64: str = ""


# Application Context object
class Context:
    def __init__(self, env: Environment):
        self.env = env


def get_context() -> Context:
    return Context(Environment())
