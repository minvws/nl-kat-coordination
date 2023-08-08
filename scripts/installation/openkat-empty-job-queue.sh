#!/bin/bash

# Stop openKAT
echo "Stopping openKAT processes"
sudo systemctl stop xtdb-http-multinode kat-rocky kat-mula kat-bytes kat-boefjes kat-normalizers kat-katalogus kat-keiko kat-octopoes kat-octopoes-worker

# Start postgres, switch to the mula_db and empty the job queue
echo "Emptying job queue"
sudo -u postgres psql mula_db > /dev/null << 'EOF'
UPDATE tasks SET status = 'CANCELLED' WHERE status = 'PENDING' and created_at < current_date
\q
EOF

# Start openKAT
echo "Starting openKAT processes"
sudo systemctl start xtdb-http-multinode kat-rocky kat-mula kat-bytes kat-boefjes kat-normalizers kat-katalogus kat-keiko kat-octopoes kat-octopoes-worker

echo "End of script. It might take a few more seconds for OpenKAT to be fully started and available."
