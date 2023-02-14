from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from boefjes.katalogus.models import RESERVED_LOCAL_ID
from boefjes.sql.db import get_engine
from boefjes.sql.db_models import RepositoryInDB


def main():
    session = sessionmaker(bind=get_engine())()

    try:
        session.add(RepositoryInDB(id=RESERVED_LOCAL_ID, name="Local Plugin Repository", base_url="http://dev/null"))
        session.commit()
    except IntegrityError:
        session.rollback()
        print("Repository Present")

    session.close()


if __name__ == "__main__":
    main()
