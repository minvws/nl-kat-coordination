"""
From:

https://github.com/bcdannyboy/CVE-2023-44487/blob/main/cve202344487.py

Basic vulnerability scanning to see if web servers may be vulnerable to CVE-2023-44487

This tool checks to see if a website is vulnerable to CVE-2023-44487 completely non-invasively.

    The tool checks if a web server accepts HTTP/2 requests without downgrading them
    If the web server accepts and does not downgrade HTTP/2 requests the tool attempts to open a connection stream and subsequently reset it
    If the web server accepts the creation and resetting of a connection stream then the server is definitely vulnerable, if it only accepts HTTP/2 requests but the stream connection fails it may be vulnerable if the server-side capabilities are enabled.


(*) Exploit by Daniel Bloom @bcdannyboy /  https://github.com/bcdannyboy

"""
from http.client import HTTPConnection, HTTPSConnection
from typing import List, Tuple, Union

import httpx
from h2.config import H2Configuration
from h2.connection import H2Connection

from boefjes.job_models import BoefjeMeta


def check_http2_support(url):
    """
    Check if the given URL supports HTTP/2.

    Parameters:
        url (str): The URL to check.

    Returns:
        tuple: (status, error/version)
        status: 1 if HTTP/2 is supported, 0 otherwise, -1 on error.
        error/version: Error message or HTTP version if not HTTP/2.
    """
    try:
        client_options = {"http2": True, "verify": False}  # Ignore SSL verification
        with httpx.Client(**client_options) as client:
            response = client.get(url)

        if response.http_version == "HTTP/2":
            return (1, "")
        return (0, f"{response.http_version}")
    except Exception as error:
        return (-1, f"check_http2_support - {error}")


def send_rst_stream_h2(scheme, host, port, stream_id, timeout=5):
    """
    Send an RST_STREAM frame to the given host and port.

    Parameters:
        host (str): The hostname.
        port (int): The port number.
        stream_id (int): The stream ID to reset.
        timeout (int): The timeout in seconds for the socket connection.

    Returns:
        tuple: (status, message)
        status: 1 if successful, 0 if no response, -1 otherwise.
        message: Additional information or error message.
    """
    try:
        if scheme == "https":
            conn = HTTPSConnection(host, port, timeout=timeout)
        else:
            conn = HTTPConnection(host, port, timeout=timeout)

        conn.connect()

        # Initiate HTTP/2 connection
        config = H2Configuration(client_side=True)
        h2_conn = H2Connection(config=config)
        h2_conn.initiate_connection()
        conn.send(h2_conn.data_to_send())

        # Send GET request headers
        headers = [(":method", "GET"), (":authority", host), (":scheme", "https"), (":path", "/")]
        h2_conn.send_headers(stream_id, headers)
        conn.send(h2_conn.data_to_send())

        # Listen for frames and send RST_STREAM when appropriate
        while True:
            data = conn.sock.recv(65535)
            if not data:
                break

            events = h2_conn.receive_data(data)
            for event in events:
                if event.stream_id == stream_id:
                    h2_conn.reset_stream(event.stream_id)
                    conn.send(h2_conn.data_to_send())
                    return (1, "")

        conn.close()
        return (0, "No response")
    except Exception as error:
        return (-1, f"send_rst_stream_h2 - {error}")


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[str, bytes]]]:
    input_ = boefje_meta.arguments["input"]
    hostname = input_["hostname"]["name"]
    ip_service = input_["ip_service"]

    scheme = ip_service["service"]["name"]
    address = ip_service["ip_port"]["address"]["address"]
    port = ip_service["ip_port"]["port"]

    output = [("URL", "Hostname", "Vulnerability Status", "Error/Downgrade Version")]
    url = f"{scheme}://{address}:{port}/"  # does not need hostname

    http2support, err = check_http2_support(url)
    if http2support == 1:
        resp, err2 = send_rst_stream_h2(scheme, hostname, port, 1)
        if resp == 1:
            output.append([url, hostname, "VULNERABLE", ""])
        elif resp == -1:
            output.append([url, hostname, "POSSIBLE", f"Failed to send RST_STREAM: {err2}"])
        elif resp == 0:
            output.append([url, hostname, "LIKELY", "Got no response from RST_STREAM request and socket closed"])
    else:
        if http2support == 0:
            output.append([url, hostname, "SAFE", f"Downgraded to {err}"])
        else:
            output.append([url, hostname, "ERROR", err])
    return [(set(), "\n".join([",".join(line) for line in output]))]
