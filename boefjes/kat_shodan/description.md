# Shodan

Shodan is a search engine that lets users search for various types of servers (webcams, routers, servers, etc.)
connected to the internet using a variety of filters. Shodan collects data mostly on web servers (HTTP or HTTPS – ports 80,
8080, 443, 8443), as well as FTP (port 21), SSH (port 22), Telnet (port 23), SNMP (port 161), IMAP (ports 143, or (
encrypted) 993), SMTP (port 25), SIP (port 5060), and Real Time Streaming Protocol (RTSP, port 554). The latter can be
used to access webcams and their video stream. KAT currently uses Shodan to scan an IpAddress for open ports with
software with known vulnerabilities.

### Input OOIs

Shodan expects an IpAddress as input.

### Output OOIs

Shodan currently outputs the following OOIs:

|OOI type|Description|
|---|---|
|IpPort|Open IpPort found on input OOI|
|CveFindingType|Known vulnerability of software behind IpPort|
|Finding|Finding|
