#!/usr/bin/bash

# Installation for Debian 11
# echo (https://docs.openkat.nl/technical_design/debianinstall.html)

# echo "number of arguments '$#'"

# Checking if at least 1 parameter was given
if [ $# -eq 0 ] || [ $# -gt 3 ]; then
	echo "Usage: ./openKAT_install.sh [debian version (11 or 12)] [openKAT version] [no_super_user]"
	exit
fi

if [ ${1} != "11" ] && [ ${1} != "12" ]; then
	echo "Debian version currently should be 11 or 12"
	exit
fi

echo "Step 0 - Preparations"

echo "Step 0.1 - Removing old install/upgrade files, update system and install curl & sudo when needed..."
rm -f kat-*.deb
rm -f xtdb-*.deb

echo "Step 0.2 - Update OS and get needed tools"
sudo apt update -y
sudo apt install curl -y
sudo apt install sudo -y

echo "Step 1 - Get latest prerelease of OpenKAT"

# The URL of the xtdb-http-multinode GitHub releases page
xtdb_url='https://github.com/dekkers/xtdb-http-multinode/releases'

# The URL of the nl-kat-coordination GitHub releases page
nl_kat_url='https://github.com/minvws/nl-kat-coordination/releases'

echo "Step 2 - Download openKAT and xtdb"

# Get the latest version of xtdb-http-multinode
echo "Step 2.1 -  Determine latest xtdb version"
xtdb_content=$(curl -s ${xtdb_url})
xtdb_version=$(echo ${xtdb_content} | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | sed 's/v//' | head -n 1)

# Get the latest version of nl-kat-coordination - handmatig instellen!
# nl_kat_content=$(curl -s $nl_kat_url)
# nl_kat_version=$(echo $nl_kat_content | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+rc[0-9]+' | sed 's/v//' | head -n 1)

# Download the latest version of xtdb-http-multinode
echo "Step 2.2 - Downloading xtdb-http-multinode version $xtdb_version..."
curl -LO "https://github.com/dekkers/xtdb-http-multinode/releases/download/v${xtdb_version}/xtdb-http-multinode_${xtdb_version}_all.deb"

# Download the latest version of nl-kat-coordination
# Let op, onderstaande link moet je zelf aanpassen
echo "Step 2.3 - Downloading nl-kat-coordination version ${2} for Debian ${1}: https://github.com/minvws/nl-kat-coordination/releases/download/v${2}/kat-debian${1}-${2}.tar.gz"
curl -LO "https://github.com/minvws/nl-kat-coordination/releases/download/v${2}/kat-debian${1}-${2}.tar.gz"

echo "Step 3 - Install openKAT and xtdb"
tar zvxf kat-*.tar.gz
sudo apt install --no-install-recommends ./kat-*_amd64.deb ./xtdb-http-multinode_*_all.deb -y

sudo systemctl start xtdb-http-multinode

echo "Step 4 - Setup postgres databases"
sudo apt install postgresql -y

sudo systemctl start postgresql

echo "Step 4.1 - Generating Passwords"
ROCKY_DB_PASSWORD=$(tr -dc A-Za-z0-9 < /dev/urandom | head -c 20)
export ROCKY_DB_PASSWORD
KATALOGUSDB_PASSWORD=$(tr -dc A-Za-z0-9 < /dev/urandom | head -c 20)
export KATALOGUSDB_PASSWORD
BYTESDB_PASSWORD=$(tr -dc A-Za-z0-9 < /dev/urandom | head -c 20)
export BYTESDB_PASSWORD
RABBITMQ_PASSWORD=$(tr -dc A-Za-z0-9 < /dev/urandom | head -c 20)
export RABBITMQ_PASSWORD
MULADB_PASSWORD=$(tr -dc A-Za-z0-9 < /dev/urandom | head -c 20)
export MULADB_PASSWORD

echo "Step 4.2 - Saving Passwords to passwords.txt"
echo "ROCKY_DB_PASSWORD=${ROCKY_DB_PASSWORD}" > passwords.txt
echo "KATALOGUSDB_PASSWORD=${KATALOGUSDB_PASSWORD}" >> passwords.txt
echo "BYTESDB_PASSWORD=${BYTESDB_PASSWORD}" >> passwords.txt
echo "RABBITMQ_PASSWORD=${RABBITMQ_PASSWORD}" >> passwords.txt
echo "MULADB_PASSWORD=${MULADB_PASSWORD}" >> passwords.txt

# Get current directory
P=`pwd`

# Load passwords for current process
source ${P}/passwords.txt

echo "Step 4.3 - RockyDB"
DB=`sudo -u postgres psql -lqt | cut -d \| -f 1 | grep rocky_db`
if [[ ${DB} == "" ]]; then
	echo "Create rocky_db..."
	sudo -u postgres createdb rocky_db
fi

U=`sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname='rocky'"|awk 'FNR == 3 {print}'|awk '{print substr($0,9,1)}'`
if [[ ${U} == "" ]]; then
	echo "Create rocky user with password ${ROCKY_DB_PASSWORD}..."
	sudo -u postgres psql -c "CREATE USER rocky WITH PASSWORD '${ROCKY_DB_PASSWORD}';"

	echo "Grant database rocky_db to rocky user..."
	sudo -u postgres psql -c 'GRANT ALL ON SCHEMA public TO rocky;' rocky_db
else
	echo "Change password rocky user to ${ROCKY_DB_PASSWORD}..."
	sudo -u postgres psql -c "ALTER USER rocky WITH PASSWORD '${ROCKY_DB_PASSWORD}';"
fi

echo "Step 4.4 - KAT-alogusDB"
DB=`sudo -u postgres psql -lqt | cut -d \| -f 1 | grep katalogus_db`
if [[ ${DB} == "" ]]; then
	echo "Create katalogus_db..."
	sudo -u postgres createdb katalogus_db
fi

U=`sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname='katalogus'"|awk 'FNR == 3 {print}'|awk '{print substr($0,9,1)}'`
if [[ ${U} == "" ]]; then
	echo "Create katalogus user with password ${KATALOGUSDB_PASSWORD}..."
	sudo -u postgres psql -c "CREATE USER katalogus WITH PASSWORD '${KATALOGUSDB_PASSWORD}';"

	echo "Grant database katalogus_db to katalogus user..."
	sudo -u postgres psql -c 'GRANT ALL ON SCHEMA public TO katalogus;' katalogus_db
else
	echo "Change password katalogus user to ${KATALOGUSDB_PASSWORD}..."
	sudo -u postgres psql -c "ALTER USER katalogus WITH PASSWORD '${KATALOGUSDB_PASSWORD}';"
fi

echo "Step 4.5 - BytesDB"
DB=`sudo -u postgres psql -lqt | cut -d \| -f 1 | grep bytes_db`
if [[ ${DB} == "" ]]; then
	echo "Create bytes_db..."
	sudo -u postgres createdb bytes_db
fi

U=`sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname='bytes'"|awk 'FNR == 3 {print}'|awk '{print substr($0,9,1)}'`
if [[ ${U} == "" ]]; then
	echo "Create bytes user with password ${BYTESDB_PASSWORD}..."
	sudo -u postgres psql -c "CREATE USER bytes WITH PASSWORD '${BYTESDB_PASSWORD}';"

	echo "Grant database bytes_db to bytes user..."
	sudo -u postgres psql -c 'GRANT ALL ON SCHEMA public TO bytes;' bytes_db
else
	echo "Change password bytes user to ${BYTESDB_PASSWORD}..."
	sudo -u postgres psql -c "ALTER USER bytes WITH PASSWORD '${BYTESDB_PASSWORD}';"
fi

echo "Step 4.5b - MulaDB"
DB=`sudo -u postgres psql -lqt | cut -d \| -f 1 | grep mula_db`
if [[ ${DB} == "" ]]; then
	echo "Create mula_db..."
	sudo -u postgres createdb mula_db
fi

U=`sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname='mula'"|awk 'FNR == 3 {print}'|awk '{print substr($0,9,1)}'`
if [[ ${U} == "" ]]; then
	echo  "Create mula user with password ${MULADB_PASSWORD}..."
	sudo -u postgres psql -c "CREATE USER mula WITH PASSWORD '${MULADB_PASSWORD}';"

	echo "Grant database muladb to mula user..."
	sudo -u postgres psql -c 'GRANT ALL ON SCHEMA public TO mula;' mula_db
else
	echo "Change password mula user to ${MULADB_PASSWORD}..."
	sudo -u postgres psql -c "ALTER USER mula WITH PASSWORD '${MULADB_PASSWORD}';"
fi

echo Step 4.6 - Update configs
echo "Step 4.6.1 - Update ROCKY_DB_PASSWORD in /etc/kat/rocky.conf to ${ROCKY_DB_PASSWORD}"
sudo sed -i "/ROCKY_DB_PASSWORD=/s/.*/ROCKY_DB_PASSWORD=${ROCKY_DB_PASSWORD}/" /etc/kat/rocky.conf

echo "Step 4.6.2 - Update BYTES_PASSWORD in /etc/kat/bytes.conf, /etc/kat/boefjes.conf, /etc/kat/mula.conf and /etc/kat/rocky.conf to ${BYTESDB_PASSWORD}"
sudo sed -i "/BYTES_PASSWORD=/s/.*/BYTES_PASSWORD=${BYTESDB_PASSWORD}/" /etc/kat/bytes.conf
sudo sed -i "/BYTES_PASSWORD=/s/.*/BYTES_PASSWORD=${BYTESDB_PASSWORD}/" /etc/kat/boefjes.conf
sudo sed -i "/BYTES_PASSWORD=/s/.*/BYTES_PASSWORD=${BYTESDB_PASSWORD}/" /etc/kat/mula.conf
sudo sed -i "/BYTES_PASSWORD=/s/.*/BYTES_PASSWORD=${BYTESDB_PASSWORD}/" /etc/kat/rocky.conf

echo "Step 4.6.3 - Update BYTES_DB_URI in /etc/kat/bytes.conf to ${BYTESDB_PASSWORD}"
sudo sed -i "/BYTES_DB_URI=/s/.*/BYTES_DB_URI=postgresql:\/\/bytes:${BYTESDB_PASSWORD}@localhost\/bytes_db/" /etc/kat/bytes.conf

echo "Step 4.6.4 - Update KATALOGUS_DB_URI in /etc/kat/boefjes.conf to ${KATALOGUSDB_PASSWORD}"
sudo sed -i "/KATALOGUS_DB_URI=/s/.*/KATALOGUS_DB_URI=postgresql:\/\/katalogus:${KATALOGUSDB_PASSWORD}@localhost\/katalogus_db/" /etc/kat/boefjes.conf

echo "Step 4.6.5 - Update SCHEDULER_DSP_BROKER_URL in /etc/kat/mula.conf to ${RABBITMQ_PASSWORD}"
sudo sed -i "/SCHEDULER_DSP_BROKER_URL=/s/.*/SCHEDULER_DSP_BROKER_URL=amqp:\/\/kat:${RABBITMQ_PASSWORD}@localhost:5672\/kat/" /etc/kat/mula.conf

echo "Step 4.6.6 - Update SCHEDULER_RABBITMQ_DSN in /etc/kat/mula.conf to ${RABBITMQ_PASSWORD}"
sudo sed -i "/SCHEDULER_RABBITMQ_DSN=/s/.*/SCHEDULER_RABBITMQ_DSN=amqp:\/\/kat:${RABBITMQ_PASSWORD}@localhost:5672\/kat/" /etc/kat/mula.conf

echo "Step 4.6.7 - Update SCHEDULER_DB_DSN in /etc/kat/mula.conf to ${MULADB_PASSWORD}"
sudo sed -i "/SCHEDULER_DB_DSN=/s/.*/SCHEDULER_DB_DSN=postgresql:\/\/mula:${MULADB_PASSWORD}@localhost\/mula_db/" /etc/kat/mula.conf

echo "Step 4.6.8 - Update QUEUE_URI in rocky.conf, bytes.conf, boefjes.conf, octopoes.conf to ${RABBITMQ_PASSWORD}"
sudo sed -i "/QUEUE_URI=/s/.*/QUEUE_URI=amqp:\/\/kat:${RABBITMQ_PASSWORD}@localhost:5672\/kat/" /etc/kat/rocky.conf
sudo sed -i "/QUEUE_URI=/s/.*/QUEUE_URI=amqp:\/\/kat:${RABBITMQ_PASSWORD}@localhost:5672\/kat/" /etc/kat/bytes.conf
sudo sed -i "/QUEUE_URI=/s/.*/QUEUE_URI=amqp:\/\/kat:${RABBITMQ_PASSWORD}@localhost:5672\/kat/" /etc/kat/boefjes.conf
sudo sed -i "/QUEUE_URI=/s/.*/QUEUE_URI=amqp:\/\/kat:${RABBITMQ_PASSWORD}@localhost:5672\/kat/" /etc/kat/octopoes.conf

echo "Step 4.7 - Initialize databases"

echo "Setp 4.7.1 - Migrating database (note: two factor message in stated in red can be ignored)..."
sudo -u kat rocky-cli migrate

echo "Step 4.7.2 - Load data..."
sudo -u kat rocky-cli loaddata /usr/share/kat-rocky/OOI_database_seed.json

echo "Step 4.7.3 - Update bytes_db..."
sudo -u kat update-bytes-db

echo "Step 4.7.4 - Update katalogus_db..."
sudo -u kat update-katalogus-db

echo "Step 4.7.5 - Upgrade mula_db..."
sudo -u kat update-mula-db

if [[ ${3} != "no_super_user" ]]; then
	echo "Step 5 - Create Superuser & dev account"
	sudo -u kat rocky-cli createsuperuser
	sudo -u kat rocky-cli setup_dev_account
else
	echo "Step 5 - Option no_super_user passed; skipping creating superuser & dev account"
fi

echo "Step 6 - RabbitMQ-server setup"

echo "Step 6.1 - Install rabbitmq-server"
sudo apt install rabbitmq-server -y

echo "Step 6.2 - Stop rabbitmq-server"
sudo systemctl stop rabbitmq-server

echo "Step 6.3 - Kill epmd"
sudo epmd -kill

echo "Step 6.4 - Add listeners to /etc/rabbitmq/rabbitmq.conf"
sudo su -c "echo listeners.tcp.local = 127.0.0.1:5672 > /etc/rabbitmq/rabbitmq.conf"

echo "Step 6.5 - Add ERL_EPMD_ADDRESS to /etc/rabbitmq/rabbitmq-env.conf"
sudo su -c "echo export ERL_EPMD_ADDRESS=127.0.0.1 > /etc/rabbitmq/rabbitmq-env.conf"

echo "Step 6.6 - Add NODENAME to /etc/rabbitmq/rabbitmq-env.conf"
sudo su -c "echo export NODENAME=rabbit@localhost >> /etc/rabbitmq/rabbitmq-env.conf"

echo "Step 6.7 - Add inet info to /etc/rabbitmq/advanced.conf"
sudo su -c "sudo cat > /etc/rabbitmq/advanced.conf << 'EOF'
[
    {kernel,[
        {inet_dist_use_interface,{127,0,0,1}}
    ]}
].
EOF"

echo "Step 6.8 - Restart rabbitmq-server"
sudo systemctl enable rabbitmq-server
sudo systemctl restart rabbitmq-server

cd /usr/lib/rabbitmq/bin

echo "Step 6.9 - Add or change kat user to rabbitmq and set password to ${RABBITMQ_PASSWORD}"
U=`sudo rabbitmqctl list_users|grep kat`
if [[ "${U}" == "" ]] ; then
	echo "Create kat user in rabbitmq with password ${RABBIT_PASSWORD}"
	sudo rabbitmqctl add_user kat ${RABBITMQ_PASSWORD}
else
	echo "Change password for the kat user to ${RABBITMQ_PASSWORD} to ensure when user already existed is set correctly"
	sudo rabbitmqctl change_password kat ${RABBITMQ_PASSWORD}
fi

echo "Step 6.10 - Add vhost kat to rabbitmq"
sudo rabbitmqctl add_vhost kat

echo "Step 6.11 - Set kat permissions in rabbitmq"
sudo rabbitmqctl set_permissions -p "kat" "kat" ".*" ".*" ".*"

cd ~

echo "Step 7 - Configure start at systemboot"
sudo systemctl enable kat-rocky kat-mula kat-bytes kat-boefjes kat-normalizers kat-katalogus kat-keiko kat-octopoes kat-octopoes-worker

echo "Step 8 - Restart KAT"
sudo systemctl restart kat-rocky kat-mula kat-bytes kat-boefjes kat-normalizers kat-katalogus kat-keiko kat-octopoes kat-octopoes-worker

echo "Step 9 - End of install openkat"
