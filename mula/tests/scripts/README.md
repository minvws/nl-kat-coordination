1. Create a `data.csv` with hostnames in this folder

Example:

```
name
mispo.es
```

2. Build and run the container:

```
$ docker build -t mula-load .
$ docker run --network="host" mula-load --orgs [number-of-orgs]
```
