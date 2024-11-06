"""This script is used to update the technologies.json file in the Wappalyzer plugin.
It downloads the latest technology data from https://github.com/enthec/webappanalyzer, a project that maintains
Wappalyzer technologies files
"""

import json

from Wappalyzer.data.update import get_technology_data

if __name__ == "__main__":
    # get the latest technology data
    data = get_technology_data()

    # write the data to the technologies.json file
    with open("technologies.json", "w") as f:
        json.dump(data, f)
