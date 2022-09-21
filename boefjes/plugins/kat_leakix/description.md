# LeakIX

LeakIX is a project goes around the Internet and finds services to index them.
They gather information on the Internet on the most common security misconfiguration currently open.

### Input OOIs

LeakIX expects an IpAddress as input.

### Output OOIs

LeakIX currently outputs the following OOIs:

|OOI type|Description|
|---|---|
|IpPort|Open IpPort found on input OOI|
|Software|Known software behind IpPort, sometimes with software version|
|CveFindingType|Known vulnerability of software behind IpPort|
|Finding|Finding|

### Running Boefje

```json
{
  "id": "leakix-scan-job",
  "module": "kat_leakix.scan",
  "organization": "_dev",
  "arguments": {
    "host": "1.1.1.1",
    "pk": "IpAddressV4|internet|1.1.1.1"
  },
  "dispatches": {
    "normalizers": [
      "kat_leakix.normalize"
    ],
    "boefjes": []
  }
}
```
