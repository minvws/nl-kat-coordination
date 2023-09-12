#!/bin/bash

# Update script for Debian. The script matches the instructions on
# https://docs.openkat.nl/technical_design/debianinstall.html

set -e

source /etc/os-release

if [ "$ID" != "debian" ]; then
    echo "The update script is only supported on Debian"
    exit 1
fi

# Check Debian version
if [ "$VERSION_ID" != "11" ] && [ "$VERSION_ID" != "12" ]; then
    echo "Only Debian version 11 and 12 are supported"
    exit 1
fi

# Checking if we don't have too many parameters
if [ $# -gt 1 ]; then
    echo "Usage: $0 [OpenKAT version]"
    exit 1
fi

debian_version=$VERSION_ID

echo "Step 0 - Get needed tools and clean up"
sudo apt -y update
sudo apt -y install curl

rm -f kat-*.deb kat-debian1[12]-*.tar.gz xtdb-*.deb

echo "Step 1 - Get latest release of OpenKAT"

# The URL of the latest xtdb-http-multinode release
xtdb_url='https://github.com/dekkers/xtdb-http-multinode/releases/latest'

# The URL of the latest nl-kat-coordination release
openkat_url='https://github.com/minvws/nl-kat-coordination/releases/latest'

echo "Step 2 - Download OpenKAT and xtdb-http-multinode"

# Get the latest version of xtdb-http-multinode
xtdb_version=$(curl -sL $xtdb_url | grep -m 1 -Po "(?<=tag\/)v[0-9\.]*(?=\")" | sed 's/^v//')

if [ $# -eq 0 ]; then
    # Get the latest version of OpenKAT if no version is specified
    openkat_version=$(curl -sL $openkat_url | grep -m 1 -Po "(?<=tag\/)v[0-9\.]*(?=\")" | sed 's/^v//')
else
    openkat_version=$1
fi

echo "Step 3 - Download the latest version of xtdb-http-multinode"
echo "Downloading xtdb-http-multinode version $xtdb_version..."
sudo curl -LO "https://github.com/dekkers/xtdb-http-multinode/releases/download/v${xtdb_version}/xtdb-http-multinode_${xtdb_version}_all.deb"

echo "Step 4 -  Download the latest version of OpenKAT"
echo "Downloading nl-kat-coordination version $openkat_version..."
sudo curl -LO "https://github.com/minvws/nl-kat-coordination/releases/download/v${openkat_version}/kat-debian${debian_version}-${openkat_version}.tar.gz"

echo "Step 5 - Install OpenKAT and xtdb-http-multinode"
sudo tar zvxf kat-*.tar.gz
sudo apt install -y --no-install-recommends ./kat-*_amd64.deb ./xtdb-http-multinode_*_all.deb

echo "Step 6 - Migrate databases"
sudo -u kat rocky-cli migrate
sudo -u kat rocky-cli loaddata /usr/share/kat-rocky/OOI_database_seed.json
sudo -u kat update-bytes-db
sudo -u kat update-katalogus-db
sudo -u kat update-mula-db

echo "Step 7 - Restart OpenKAT"
sudo systemctl restart xtdb-http-multinode kat-rocky kat-mula kat-bytes kat-boefjes kat-normalizers kat-katalogus kat-keiko kat-octopoes kat-octopoes-worker

echo "End of OpenKAT update script"
