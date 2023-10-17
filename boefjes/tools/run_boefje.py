#!/usr/bin/env python3
# ruff: noqa: E402

import logging
import pdb
import sys
import uuid
from pathlib import Path

import click

sys.path.append(str(Path(__file__).resolve().parent.parent))

from boefjes.job_handler import BoefjeHandler
from boefjes.job_models import Boefje, BoefjeMeta
from boefjes.katalogus.local_repository import get_local_repository
from boefjes.local import LocalBoefjeJobRunner

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


@click.command()
@click.option("--pdb", "start_pdb", is_flag=True, help="Start pdb on exceptions")
@click.argument("organization_code")
@click.argument("boefje_id")
@click.argument("input_ooi")
def run_boefje(start_pdb, organization_code, boefje_id, input_ooi):
    """Run boefje"""

    meta = BoefjeMeta(id=uuid.uuid4(), boefje=Boefje(id=boefje_id), organization=organization_code, input_ooi=input_ooi)

    local_repository = get_local_repository()

    handler = BoefjeHandler(LocalBoefjeJobRunner(local_repository), local_repository)
    try:
        handler.handle(meta)
    except Exception:
        if start_pdb:
            pdb.post_mortem()

        raise


if __name__ == "__main__":
    run_boefje()
