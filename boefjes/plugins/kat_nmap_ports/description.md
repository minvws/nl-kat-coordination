# Nmap Ports

Nmap is a network scanning tool that uses IP packets to identify all the devices connected to a network and to provide
information on the services and operating systems they are running. In KAT, a Python wrapper around Nmap is used to find
open ports with their services of an IpAddress. Nmap itself runs in a temporary Docker container. This boefje allows to
scan specific ports.

### Options

This Nmap boefje has the following hardcoded options:

| Option | Function |
| ----------- | ----------- |
| `T4` | assume a fast and reliable network |
| `Pn` | skips host discovery, treats hosts as online |
|`-r` | scan ports in order |
|`-v10` |use verbosity level 10 |
|`-sV` |probe open ports to determine version info |
|`-sS` |scan TCP SYN |
|`-sU` |Scan UDP (slower) |
|`-oX` |Output in XML |

The PORTS variable is given as the argument for `-p` (see the Nmap documentation for more information).

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

The boefje uses the same normalizer and structure as the generic `kat_nmap` boefje.

**Cat name**: Elsje (inverted)
