This is an external assets database boefje that adds the IPs, netblocks and hostnames from an external API to KAT. As there is no real input for this boefje, it runs on the network object (usually "internet").

To make the API call work, there are four environment variables:

- `DB_URL`; the URL where the API for the database lives (without path, with port), for example `http://host.docker.internal:9000`.
- `DB_ACCESS_TOKEN`; an API access token as `GET` parameter.
- `DB_ORGANIZATION_IDENTIFIER`; by default uses the organisation ID in KAT. If this is not preferred it can be changed to something else. Otherwise, make sure that the organization code in kat matches the id of the organisation in the database.
- `DB_ENDPOINT_FORMAT`; a Python format string with all variables above (optionally empty) and any path specifics of the API. E.g. `{DB_URL}/api/v1/participants/assets/{DB_ORGANIZATION_IDENTIFIER}?access_token={DB_ACCESS_TOKEN}' (without quotes)`

The response expected is JSON of the form

```json
{
    "ip_key1":
        ...
        "ip_keyN": [{"ip_item_key1": "ip_item_keyN": IPv4/6}],
    "domain_key1":
        ...
        "domain_keyN": [{"domain_item_key1": "domain_item_keyN": hostname}]
}
```

For example:

```json
{
    "ip_addresses": [{"ip_address": "198.51.100.2"}, {"ip_address": "2001:db8:ffff:ffff:ffff:ffff:ffff:ffff"}, {"ip_address": "192.0.2.0/24"}],
    "domains": [{"domain": "example.com"}]
}
```

The expected ip and domain (item) key lists can be configured in `normalize.py`. Ranges are expected as strings in CIDR notation. Clearance level for fetched items is set to `L0`. Reference implementation of the API server is in the works.
