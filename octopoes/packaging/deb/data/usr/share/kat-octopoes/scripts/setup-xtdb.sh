#!/bin/bash -e

XTDB_VERSION=1.21.0
XTDB_DATA_DIR=/var/lib/xtdb

/usr/sbin/adduser --system --home /opt/xtdb --no-create-home --group xtdb

apt install -y default-jre-headless wget

if [ ! -d /opt/xtdb ]; then
    mkdir /opt/xtdb
    chown root:xtdb /opt/xtdb
    chmod 750 /opt/xtdb
fi

wget -O /opt/xtdb/xtdb-standalone-rocksdb.jar https://github.com/xtdb/xtdb/releases/download/${XTDB_VERSION}/xtdb-standalone-rocksdb.jar

if [ ! -d /etc/xtdb ]; then
    mkdir /etc/xtdb
    chown root:xtdb /etc/xtdb
    chmod 750 /etc/xtdb
fi

if [ ! -d ${XTDB_DATA_DIR} ]; then
    mkdir ${XTDB_DATA_DIR}
    chown xtdb:xtdb ${XTDB_DATA_DIR}
    chmod 750 ${XTDB_DATA_DIR}
fi

if [ ! -f /etc/xtdb/xtdb_default.edn ]; then
    cat > /etc/xtdb/xtdb_default.edn << EOF
{
  :xtdb.http-server/server {
    :port 3000
    :jetty-opts {:host "127.0.0.1"}
  }
  :xtdb.rocksdb/block-cache {
    :xtdb/module xtdb.rocksdb/->lru-block-cache
    :cache-size 536870912
  }
  :xtdb/tx-log {
    :kv-store {
      :xtdb/module xtdb.rocksdb/->kv-store
      :block-cache :xtdb.rocksdb/block-cache
      :db-dir "${XTDB_DATA_DIR}/default_tx-log"
    }
  }
  :xtdb/document-store {
    :kv-store {
      :xtdb/module xtdb.rocksdb/->kv-store
      :block-cache :xtdb.rocksdb/block-cache
      :db-dir "${XTDB_DATA_DIR}/default_documents"
    }
  }
  :xtdb/index-store {
    :kv-store {
      :xtdb/module xtdb.rocksdb/->kv-store
      :block-cache :xtdb.rocksdb/block-cache
      :db-dir "${XTDB_DATA_DIR}/default_indexes"
    }
  }
}

EOF

    chown xtdb:xtdb /etc/xtdb/xtdb_default.edn
    chmod 640 /etc/xtdb/xtdb_default.edn
fi

if [ ! -f /etc/xtdb/environment.conf ]; then
    cat > /etc/xtdb/environment.conf << EOF
MALLOC_ARENA_MAX=2
MAX_MEMORY=512M
MAX_DIRECT_MEMORY=512M
EOF

    chown xtdb:xtdb /etc/xtdb/environment.conf
    chmod 640 /etc/xtdb/environment.conf
fi

if [ ! -f /usr/lib/systemd/system/xtdb@.service ]; then
    cat > /usr/lib/systemd/system/xtdb@.service << EOF
[Unit]
Description=XTDB standalone for client %I
After=network-online.target

[Service]
Type=simple
User=xtdb
Group=xtdb
WorkingDirectory=/opt/xtdb
EnvironmentFile=/etc/xtdb/environment.conf
ExecStart=/usr/bin/java \\
    -Xms128M -Xmx\${MAX_MEMORY} \\
    -XX:MaxDirectMemorySize=\${MAX_DIRECT_MEMORY} \\
    -jar /opt/xtdb/xtdb-standalone-rocksdb.jar -f /etc/xtdb/xtdb_%i.edn

[Install]
WantedBy=multi-user.target

EOF

    chmod 750 /usr/lib/systemd/system/xtdb@.service
    systemctl enable --now xtdb@default.service
fi
