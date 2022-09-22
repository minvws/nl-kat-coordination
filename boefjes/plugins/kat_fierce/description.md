# Fierce

Fierce is a semi-lightweight scanner that helps locate non-contiguous IP space and hostnames against specified domains.
It's really meant as a pre-cursor to nmap, unicornscan, nessus, nikto, etc, since all of those require that you already
know what IP space you are looking for. This does not perform exploitation and does not scan the whole internet
indiscriminately. It is meant specifically to locate likely targets both inside and outside a corporate network. Because
it uses DNS primarily you will often find mis-configured networks that leak internal address space. That's especially
useful in targeted malware. KAT uses fierce with the module from `https://github.com/mschwager/fierce`.

### Options

There are three lists of common subdomains that can be used to scan:

|Name|Length|Description|
|---|---|---|
|default.txt|1594|A short list for fast scanning|
|5000.txt|5000|A list with the 5000 most common subdomains|
|20000.txt|20000|A list with all known common subdomains|

Easy switching between lists is currently not possible, switching has to be done in the code of the Boefje.

### Input OOIs

Fierce expects a hostname without a subdomain as input. All hostnames can be given as input, but nameservers or
subdomains do not yield results.

### Output OOIs

Fierce outputs the following OOIs:

|OOI type|Description|
|---|---|
|Hostname|Subdomain of the Hostname input OOI|
|IpAddress|IpAddress of subdomain, can be IpAddressV4 or IpAddressV6|
|DnsRecord|DnsRecord that couples the output Hostname to the output IpAddress, can be DnsARecord or DnsAaaaRecord|
