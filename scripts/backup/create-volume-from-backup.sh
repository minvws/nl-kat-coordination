#!/bin/bash
# creates a docker volume from a backup
set -eu

while [ $# -gt 0 ]; do
  case "$1" in
    -v|-volume|--volume)
      volume="$2"
      ;;
    -p|-path|--path)
      backup_path="$2"
      ;;
    -n|-volume-name|--volume-name)
      volume_name="$2"
      ;;
    -s|-snapshot|--snapshot)
      snapshot="$2"
      ;;
    -h|-help|--help)
      printf -- "-v | --volume: the volume name in the backup\n"
      printf -- "-n | --volume-name (optional): create the restore as this new volume name\n"
      printf -- "-p | --path: the storage path of the backup location\n"
      printf -- "-s | --snapshot: the snapshot to restore\n"
      exit 1
      ;;
    *)
      printf "***************************\n"
      printf "* Error: Invalid argument.*\n"
      printf "***************************\n"
      exit 1
  esac
  shift
  shift
done

if [ -z "${volume_name:-}" ]; then
  volume_name="$volume"
fi

volume_exists="$(docker volume ls | grep -q "$volume_name")"
if [ "$volume_exists" ]; then
  printf "***********************************\n"
  printf "Error: volume %s exists. \n" "$volume_name"
  printf "Please delete before proceeding    \n"
  printf "***********************************\n"
  exit 1
fi

# If no snapshot is given, find the newest snapshot in the backup_path/volume
# Does not use ls in order to keep doing the correct thing even with special
# characters like newlines in the filenames.
if [ -z "${snapshot:-}" ]; then
  NEWEST=0
  for dirent in "${backup_path}/${volume}"/*; do
    # Get the modification time of the directory entry with stat in unix time
    MTIME="$(stat --format="%Y" "$dirent")"
    if [ "$MTIME" -gt "$NEWEST" ]; then
      NEWEST="$MTIME"
      snapshot="$dirent"
    fi
  done
  snapshot="$(basename "$snapshot")"
fi

if [ -z "${snapshot:-}" ]; then
  printf "**********************************\n"
  printf "* Error: Unable to find snapshot.*\n"
  printf "**********************************\n"
  exit 1
else
  echo "creating from snapshot: ${snapshot}"
fi

uuid="$(cat /proc/sys/kernel/random/uuid)"
cwd="$(pwd)"

IMAGE=alpine:latest
docker run \
--mount "type=volume,src=${volume_name},dst=/data" \
--name "$uuid" \
"$IMAGE"

mkdir "/tmp/$uuid"
tar -xf "$backup_path/$volume/$snapshot" -C "/tmp/$uuid"
cd "/tmp/$uuid"

docker cp -a . "$uuid:/data"
docker rm "$uuid"
cd "$cwd"
