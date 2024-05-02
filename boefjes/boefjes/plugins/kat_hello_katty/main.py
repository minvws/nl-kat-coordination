import json
from os import getenv

def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    """Function that gets ran to give raw data for the normalizers that read from """   
    address = boefje_meta["arguments"]["input"]["address"]
    MESSAGE = getenv("MESSAGE", "ERROR")
    NUMBER = getenv("NUMBER", "1")

    # Check if NUMBER has been given, if it has not. Keep it at 0
    amount_of_emoji = 0
    if NUMBER != "":
        try:
            amount_of_emoji = int(NUMBER)
        except:
            pass

    emojis = "😺" * amount_of_emoji
    greeting = f"{MESSAGE} {emojis}!!!"
    
    raw = json.dumps({
        "address": address,
        "greeting": greeting
    })
    
    
    return [
        (set(), raw)
    ]