from boefjes.config import BASE_DIR


def get_dummy_data(filename: str) -> bytes:
    path = BASE_DIR / ".." / "tests" / "examples" / filename
    return path.read_bytes()
