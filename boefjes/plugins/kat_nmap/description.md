# Nmap

Nmap is a network scanning tool that uses IP packets to identify all the devices connected to a network and to provide
information on the services and operating systems they are running. In KAT, a Python wrapper around Nmap is used to find
open ports with their services of an IpAddress. 
### Options

This Nmap has the following hardcoded options:

For TCP ports:
`"-T4", "-Pn", "-r", "-v10", "-sV", "-sS", "-p-"`

For UDP ports:
`"-T4", "-Pn", "-r", "-v10", "-sV", "-sU"`

### Input OOIs

Nmap expects an IpAddress as input which can be of type IpAddressV4 or IpAddressV6.

### Output OOIs

Nmap outputs the following OOIs:

|OOI type|Description|
|---|---|
|IpPort|Open ports of IpAddress|
|Service|Services that are found|
|IpService|IpService that couples a service to an open port|
|Finding|Finding if ports are open that should not be open (TEMP!)|
|KatFindingType|FindingType if ports are open that should not be open (TEMP!)|
### Running Boefje

```json
{
  "id": "nmap-scan-job",
  "module": "kat_nmap.scan",
  "organization": "_dev",
  "arguments": {
    "host": "1.1.1.1"
  },
  "dispatches": {
    "normalizers": [
      "kat_nmap.normalize"
    ],
    "boefjes": []
  }
}
```

### Boefje structure

```
boefjes/tools/kat_nmap
├── normalize.py
├── scan.py
└── requirements.txt
```
