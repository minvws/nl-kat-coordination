from boefjes.config import settings


def get_dummy_data(filename: str) -> bytes:
    path = settings.BASE_DIR / ".." / "tests" / "examples" / filename
    return path.read_bytes()
