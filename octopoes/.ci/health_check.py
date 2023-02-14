import sys
import urllib.request

url = sys.argv[1]
with urllib.request.urlopen(url) as response:
    if response.status != 200:
        exit(1)
