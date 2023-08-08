#!/bin/bash

echo "Restarting openKAT..."
sudo systemctl restart xtdb-http-multinode kat-rocky kat-mula kat-bytes kat-boefjes kat-normalizers kat-katalogus kat-keiko kat-octopoes kat-octopoes-worker
