# Roeltje is the browser/integration test-suite for Rocky

For now there is only 1 environment: http://localhost:8000

requirements:

- yarn

... and make sure you have the correct user credentials in fixtures/users.json

to install:

```
$ make build
```

to open cypress UI:

```
$ make run
```

to run tests headless:

```
$ make test
```
