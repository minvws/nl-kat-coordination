# Censys

Censys is a search engine similar to Shodan. It continually scans the entire public IPv4 address space on 3,592+ ports using automatic protocol detection and also leverages redirects and the Domain Name System to discover and scan (~39M) in-use IPv6 addresses.
Performing a scan requires an account. You can sign up for a free account at https://accounts.censys.io/register . After registration you can obtain an API ID and SECRET which have to be used in order for this boefje to work.

The GUI of the search engine can be found at https://search.censys.io

### Input OOIs

Censys expects an IpAddress or Hostname as input.

### Output OOIs

Censys currently outputs the following OOIs:

|OOI type|Description|
|---|---|
|IpPort|Open IpPort found on input OOI|
