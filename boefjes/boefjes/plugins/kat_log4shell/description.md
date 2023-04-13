# Log4shell

Log4shell is a popular name for [CVE-2021-44228](https://nvd.nist.gov/vuln/detail/CVE-2021-44228).
This vulnerability allows attackers to perform remote code execution (RCE).
This Boefje tries to inject very low impact payload to check whether your application is exposed.

### Input OOIs

Log4shell scan expects a URL object as input.

### Output OOIs

Currently, output needs to be verified from the `REPLY_FQDN`. In the future Log4shell outputs the following OOIs:

| OOI type | Description                |
| -------- | -------------------------- |
| Finding  | Finding if RCE is possible |

### Running Boefje

```json
{
  "id": "random-uuid",
  "organization": "_dev",
  "input_ooi":"URL|internet|127.0.0.1|tcp|443|http|internet|test.test.test|/",
  "arguments": {
    "url": "https://test.test.test/"
  },
  "dispatches": {
    "normalizers": [],
    "boefjes": []
  }
}

```

### Boefje structure

```
boefjes/tools/kat_log4shell
├── log4jcheck.py
```
