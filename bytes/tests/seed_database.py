import uuid

from bytes.database.sql_meta_repository import create_meta_data_repository
from bytes.models import RawData
from tests.loading import get_boefje_meta


def seed():
    repository = next(create_meta_data_repository())
    number_of_raw_files, chunk_size = int(2e6), 1000

    for i in range(int(number_of_raw_files / chunk_size)):
        with repository:
            for j in range(chunk_size):
                raw = b"asdf           ---                \n\n testdata" + str(i).encode()

                boefje_meta = get_boefje_meta(meta_id=str(uuid.uuid4()))
                boefje_meta.organization = ["a", "b", "c", "d", "e", "f", "g"][i % 7]

                repository.save_boefje_meta(boefje_meta)
                repository.save_raw(RawData(value=raw, boefje_meta=boefje_meta))

            print(f"Committing chunk {i}")


if __name__ == "__main__":
    """This script is just a helper to generate a large set of objects to test performance with."""

    seed()
