from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from sql.db import get_engine
from sql.db_models import OrganisationInDB, RepositoryInDB


def main():
    session = sessionmaker(bind=get_engine())()

    try:
        session.add(OrganisationInDB(id="_dev", name="Development Organisation"))
        session.commit()
    except IntegrityError:
        session.rollback()
        print("Organisation Present")

    try:
        session.add(
            RepositoryInDB(
                id="LOCAL", name="Local Plugin Repository", base_url="http://dev/null"
            )
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        print("Repository Present")

    session.close()


if __name__ == "__main__":
    main()
