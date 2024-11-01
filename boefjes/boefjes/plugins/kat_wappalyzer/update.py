import json

from Wappalyzer.data.update import get_technology_data

if __name__ == "__main__":
    data = get_technology_data()
    with open("technologies.json", "w") as f:
        json.dump(data, f)
