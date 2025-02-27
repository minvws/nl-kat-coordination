# Nuclei - Project discovery

Nuclei is used to send requests across targets based on a template, leading to zero false positives
and providing fast scanning on a large number of hosts. Nuclei offers scanning for a variety of protocols,
including TCP, DNS, HTTP, SSL, File, Whois, Websocket, Headless etc. With powerful and flexible templating,
Nuclei can be used to model all kinds of security checks.

Integrated in this Boefje are only the CVE templates for performance reasons.

[More information about Nucelei](https://github.com/projectdiscovery/nuclei)

### Input OOIs

Nuclei expects a Hostname/HostnameHTTPURL object of a website as input. The scan will then use the [CVE directory](https://github.com/projectdiscovery/nuclei-templates/tree/main/cves)
to scan for known CVE's

this is handled by the following parameter in the "main.py" file

```
   "-t", "/root/nuclei-templates/cves/"
```

### Output OOIs

Nuclei outputs the following OOIs:

| OOI type       | Description                                 |
| -------------- | ------------------------------------------- |
| CveFindingType | Returns CVE's found on the target hostnames |
| Finding        | Finding                                     |
