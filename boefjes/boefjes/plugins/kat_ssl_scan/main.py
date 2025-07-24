import subprocess

TLS_CAPABLE_SERVICES = ("https", "ftp", "ftps", "smtps", "xmpp", "imaps", "pop3s", "pop3", "ldap", "mysql", "ssh", "rpd")

def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    input_ = boefje_meta["arguments"]["input"]
    hostname = None
    if "hostname" in input.keys():
        # we are dealing with a website
        hostname = input_["hostname"]["name"]
        ip = input_["ip_service"]["ip_port"]["address"]["address"]
        port = input_["ip_service"]["ip_port"]["ip"]
        servicename = input_["ip_service"]["service"]["name"]
    else:
        # we are dealing with an IP-servive        
        ip = input_["ip_port"]["address"]["address"]
        port = input_["ip_port"]["ip"]        
        servicename = input_["service"]["name"]
    
    if servicename not in TLS_CAPABLE_SERVICES:
        return [({"info/boefje"}, "Skipping check due to non-TLS service")]

    command = ["/usr/bin/sslscan", "--no-colour", "--show-sigs"]
    if servicename in ("pop3", "ftp", "mysql"):
        command.append("-starttls")
    elif servicename == "ldap":
        command.append("--starttls-ldap")
    elif servicename == "rpd":
        command.append("-rdp")
    elif servicename == "https" and hostname:
        command.extend(["--sni-name=", hostname])

    command.extend([ "--xml=-", ip])
    output = subprocess.run(command, capture_output=True)
    output.check_returncode()

    return [({"openkat/ssl-scan-output"}, output.stdout.decode())]
