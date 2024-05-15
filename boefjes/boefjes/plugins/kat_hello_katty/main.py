import json
import logging
from os import getenv


def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    """Function that gets ran to give raw data for the normalizers that read from"""
    address = boefje_meta["arguments"]["input"]["address"]
    MESSAGE = getenv("MESSAGE", "ERROR")
    NUMBER = getenv("NUMBER", "0")

    # Check if NUMBER has been given, if it has not. Keep it at 0
    amount_of_cats = 0
    if NUMBER != "":
        try:
            amount_of_cats = int(NUMBER)
        except (TypeError, ValueError) as e:
            logging.error("NUMBER value was not of correct type: %s", e)

    cats = "😺" * amount_of_cats
    greeting = f"{MESSAGE}{cats}!!!"

    raw_data = json.dumps({"address": address, "greeting": greeting})

    return [(set(), raw_data)]
