# WP scan

The WPScan is a black box WordPress security scanner written for security professionals and blog maintainers to test the
security of their WordPress sites. The WPScan tool uses a database of 23,679 WordPress vulnerabilities. WPScan requires
an API key when performing less than 25 scans per day.

### Input OOIs

Shodan expects a Url object of a WordPress website as input. Performing the WPScan on a non-WordPress website yields no
results.

### Output OOIs

WPScan outputs the following OOIs:

|OOI type|Description|
|---|---|
|CveFindingType|Known vulnerability of WordPress or WordPress plugins on the input Url|
|Finding|Finding|
