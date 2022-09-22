#!/bin/bash -e
# ENV:
# BUILD_DIR - directory where package files will be placed
# RELEASE_VERSION - debian package version
# RELEASE_TAG - reference to repository state
# PKG_NAME - name of package
# REPOSITORY - github repository (owner/repos-name)

if [[ -z "$BUILD_DIR" || -z "$RELEASE_VERSION" || -z "$RELEASE_TAG" || -z "$PKG_NAME" || -z "$REPOSITORY" ]]; then
    echo "Missing one or more environment variables for building debian package."
    head -n 8 $0 | tail -n 6
    exit 1
fi

PKG_DIR=${PKG_NAME}_${RELEASE_VERSION}
PACKAGE_FILES=(scheduler
.env-dist
README.md
logging.json
logging.prod.json
LICENSE
requirements.txt
)

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

echo "Create copyright file"
sed -i "s|__URL__|https://github.com/${REPOSITORY}|" ${BUILD_DIR}/${PKG_DIR}/debian/copyright
cat LICENSE | sed 's/^/  /' >> ${BUILD_DIR}/${PKG_DIR}/debian/copyright

apt update
apt install gettext devscripts debhelper -y

echo "Build package"
cd ${BUILD_DIR}/${PKG_DIR}/
dpkg-buildpackage -us -uc -b

cd ../..
rm -r ${BUILD_DIR}/${PKG_DIR}/
