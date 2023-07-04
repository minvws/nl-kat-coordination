#!/usr/bin/bash

# Installation for Debian 11
# echo (https://docs.openkat.nl/technical_design/debianinstall.html)

# Check if version parameter was given
if [ $# -lt 2 ] || [ $# -gt 2 ]; then
        echo "Usage ./openKAT_upgrade.sh [11|12] [openKAT version]"
        exit
fi

# check Debian version parameter (should be 11 or 12)
if [ ${1} != "11" ] && [ ${1} != "12" ]; then
        echo "Debian version currently should be 11 or 12"
        exit
fi

echo "Step 0 - Get needed tools - toegevoegd"
sudo apt update -y
sudo apt install curl -y
sudo apt install sudo -y

# ls -l
rm -f kat-*
rm -f xtdb-*

echo "Step 1 - Get latest prerelease of openKAT"

# The URL of the xtdb-http-multinode GitHub releases page
xtdb_url='https://github.com/dekkers/xtdb-http-multinode/releases'

# The URL of the nl-kat-coordination GitHub releases page
#nl_kat_url='https://github.com/minvws/nl-kat-coordination/releases'

echo "Step 2 - Download OpenKAT and xtdb"

# Get the latest version of xtdb-http-multinode
xtdb_content=$(curl -s $xtdb_url)
xtdb_version=$(echo $xtdb_content | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | sed 's/v//' | head -n 1)

# Get the latest version of nl-kat-coordination - handmatig instellen!
# nl_kat_content=$(curl -s $nl_kat_url)
# nl_kat_version=$(echo $nl_kat_content | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+rc[0-9]+' | sed 's/v//' | head -n 1)

echo "Step 3 - Download the latest version of xtdb-http-multinode"
echo "Downloading xtdb-http-multinode version $xtdb_version..."
sudo curl -LO "https://github.com/dekkers/xtdb-http-multinode/releases/download/v${xtdb_version}/xtdb-http-multinode_${xtdb_version}_all.deb"

echo "Step 4 -  Download the latest version of nl-kat-coordination"
echo "Downloading nl-kat-coordination version ${1}..."
sudo curl -LO "https://github.com/minvws/nl-kat-coordination/releases/download/v${2}/kat-debian${1}-${2}.tar.gz"

echo "Step 5 - Install openKAT and xtdb"
sudo tar zvxf kat-*.tar.gz
sudo apt install --no-install-recommends ./kat-*_amd64.deb ./xtdb-http-multinode_*_all.deb -y

echo "Step 6 - Migrate databases (note: ignore two factor message in red)"
sudo -u kat rocky-cli migrate
sudo -u kat rocky-cli loaddata /usr/share/kat-rocky/OOI_database_seed.json
sudo -u kat update-bytes-db
sudo -u kat update-katalogus-db
sudo -u kat update-mula-db

echo "Step 7 - Restart KAT"
sudo systemctl restart xtdb-http-multinode kat-rocky kat-mula kat-bytes kat-boefjes kat-normalizers kat-katalogus kat-keiko kat-octopoes kat-octopoes-worker

echo "End of script"
