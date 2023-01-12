# Nmap IP-range

This boefje checks an IP range/NetBlock and stores any IP addresses that seem to be active.

### Options

This Nmap boefje has the following hardcoded options:

| Option | Function |
| ----------- | ----------- |
| `T4` | assume a fast and reliable network |
| `Pn` | skips host discovery, treats hosts as online |
|`-r` | scan ports in order |
|`-v10` |use verbosity level 10 |
|`-oX` |Output in XML |

For TCP `-sS` is used, for UDP `-sU` is used. Both have their own TOP_PORTS argument.

### Input OOIs

Nmap expects an NetBlock as input.

### Output OOIs

Nmap outputs the following OOIs:

|OOI type|Description|
|---|---|
|IPAddressV4 | IPv4 |
|IPAddressV6 | IPv6 |
|IpPort|Open ports of IpAddress|
|Service|Services that are found|
|IpService|IpService that couples a service to an open port|

The boefje uses the same normalizer and structure as the generic `kat_nmap` boefje.

**Cat name**: Elsje (inverted, mirrored)
