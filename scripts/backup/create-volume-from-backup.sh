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
      printf -- "-v | --volume: create the backup name of the volume\n"
      printf -- "-n | --volume-name (optional): create the backup as this volume name\n"
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

if [ -z "${snapshot:-}" ]; then
  snapshot="$(ls -At "${backup_path}/${volume}/" | tail -n 1)"
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
