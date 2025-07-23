# Nmap

Nmap is a network scanning tool that uses IP packets to identify all the devices connected to a network and to provide
information on the services and operating systems they are running. In KAT, a Python wrapper around Nmap is used to find
open ports with their services of an IpAddress. Nmap itself runs in a temporary Docker container.

### Options

This Nmap has the following hardcoded options:

| Option | Function                                     |
| ------ | -------------------------------------------- |
| `T4`   | assume a fast and reliable network           |
| `Pn`   | skips host discovery, treats hosts as online |
| `-r`   | scan ports in order                          |
| `-v10` | use verbosity level 10                       |
| `-sV`  | probe open ports to determine version info   |
| `-oX`  | Output in XML                                |
| `-sU`  | UDP scan                                     |

`TOP_PORTS_UDP` defaults to `250`.

### Input OOIs

Nmap expects an IpAddress as input which can be of type IpAddressV4 or IpAddressV6.

### Output OOIs

Nmap outputs the following OOIs:

| OOI type       | Description                                                   |
| -------------- | ------------------------------------------------------------- |
| IpPort         | Open ports of IpAddress                                       |
| Service        | Services that are found                                       |
| IpService      | IpService that couples a service to an open port              |
| Finding        | Finding if ports are open that should not be open (TEMP!)     |
| KatFindingType | FindingType if ports are open that should not be open (TEMP!) |

### Running Boefje

```json
{
  "id": "nmap-scan-job",
  "organization": "_dev",
  "arguments": {
    "host": "1.1.1.1"
  },
  "dispatches": {
    "normalizers": ["kat_nmap.normalize"],
    "boefjes": []
  }
}
```

### Boefje structure

```
boefjes/tools/kat_nmap
├── normalize.py
├── main.py
```

**Cat name**: Elsje
