#!/bin/bash
# ENV:
# BUILD_DIR - directory where package files will be placed
# RELEASE_VERSION - debian package version
# RELEASE_TAG - reference to repository state
# PKG_NAME - name of package
# REPOSITORY - github repository (owner/repos-name)
# OCTOPOES_DIR - (optional) path to octopoes repos to add to package.
#                When omitted octopoes will be downloaded at installation.

if [[ -z "$BUILD_DIR" || -z "$RELEASE_VERSION" || -z "$RELEASE_TAG" || -z "$PKG_NAME" || -z "$REPOSITORY" ]]; then
    echo "Missing one or more environment variables for building debian package."
    head -n 10 $0 | tail -n 8
    exit 1
fi

PKG_DIR=${PKG_NAME}_${RELEASE_VERSION}

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

set -e

PACKAGE_FILES=(rocky
account
assets
crisis_room
data
export_migrations
fmea
locale
onboarding
katalogus
roeltje
templates
tools
.env-dist
LICENSE
manage.py
OOI_database_seed.json
package.json
Readme.md
requirements.txt
yarn.lock)

echo "Build frontend"
nvm install v16
nvm use
npm install -g yarn
yarn
yarn build

# TODO: proper deb package versions
echo "Create packaging directory"
mkdir -p ${BUILD_DIR}/${PKG_DIR}/{data/usr/share/${PKG_NAME}/app,data/usr/bin,debian}

echo "Move files to the packaging directory"
for file in "${PACKAGE_FILES[@]}"; do
    cp -r $file ${BUILD_DIR}/${PKG_DIR}/data/usr/share/${PKG_NAME}/app/
done

cp -r ./packaging/deb/* ${BUILD_DIR}/${PKG_DIR}/
sed -i "s/_VERSION_/${RELEASE_VERSION}/g" ${BUILD_DIR}/${PKG_DIR}/debian/control

# TODO: generate proper changelog
echo "Create changelog file"
cat > ${BUILD_DIR}/${PKG_DIR}/debian/changelog << EOF
${PKG_NAME} (${RELEASE_VERSION}) unstable; urgency=low
  * view changes: https://github.com/${REPOSITORY}/releases/tag/${RELEASE_TAG}

 -- OpenKAT <maintainer@openkat.nl>  $(LANG=C date -R)

EOF

if [ -n "${OCTOPOES_DIR}" ]; then
  echo "Add octopoes to package"
  OCTOPOES_VER=$(grep git requirements.txt | awk -F '@' '{ print $3 }')
  git clone --depth 1 --branch ${OCTOPOES_VER} file://${OCTOPOES_DIR} ${BUILD_DIR}/${PKG_DIR}/data/usr/share/${PKG_NAME}/octopoes
  rm -r ${BUILD_DIR}/${PKG_DIR}/data/usr/share/${PKG_NAME}/octopoes/{.git,.ci,.github,Dockerfile} || true
fi

echo "Create copyright file"
sed -i "s|__URL__|https://github.com/${REPOSITORY}|" ${BUILD_DIR}/${PKG_DIR}/debian/copyright
cat LICENSE | sed 's/^/  /' >> ${BUILD_DIR}/${PKG_DIR}/debian/copyright

DEBIAN_FRONTEND=noninteractive apt install gettext devscripts debhelper -y

echo "Build package"
cd ${BUILD_DIR}/${PKG_DIR}/
dpkg-buildpackage -us -uc -b

cd ../..
rm -r ${BUILD_DIR}/${PKG_DIR}/
