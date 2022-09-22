# DNS

The DNS lookup tool fetches all the DNS records for a domain. To do that it uses the dsnpython package. Currently, only
A, AAAA, ans MX records are modelled.

### Input OOIs

DNS scan expects a Hostname object as input.

### Output OOIs

DNS outputs the following OOIs:

|OOI type|Description|
|---|---|
|Hostname|Hostnames of nameservers of input OOI, one of which will be the the SOA|
|DnsZone|DnsZone of the input OOI, found nameservers will be added as DnsNameServerHostnames|
|IpAddress|IpAddresses of input Hostname, can be IpAddressV4 or IpAddressV6|
|DnsRecord|DnsRecord that couples the input Hostname to the output IpAddresses, can be DnsARecord or DnsAaaaRecord|
