#!/bin/sh
set -e
# Generate the Apache basic-auth file from the configured credentials on every
# start so WEBDAV_USER / WEBDAV_PASSWORD can be changed via the environment.
echo "${WEBDAV_USER}:$(openssl passwd -apr1 "${WEBDAV_PASSWORD}")" > /usr/local/apache2/conf/webdav.passwd
exec "$@"
