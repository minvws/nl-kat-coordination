import subprocess


def verify_hostname_meta(input_ooi):
    # if the input object is HostnameHTTPURL then the hostname is located in netloc
    if "netloc" in input_ooi and "name" in input_ooi["netloc"]:
        netloc_name = input_ooi["netloc"]["name"]
        port = input_ooi["port"]
        return f"{netloc_name}:{port}"
    else:
        # otherwise the Hostname input object is used
        return input_ooi["name"]


def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    # Checks if the url is of object HostnameHTTPURL or Hostname
    url = verify_hostname_meta(boefje_meta["arguments"]["input"])
    cmd = ["nmap"] + boefje_meta["arguments"]["oci_arguments"] + ["-u", url]

    return [({"openkat/nuclei-output"}, subprocess.run(cmd, capture_output=True).stdout.decode())]
