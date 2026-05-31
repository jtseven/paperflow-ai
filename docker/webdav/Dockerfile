# WebDAV drop-box in front of Paperless' consume folder.
# Documents uploaded over WebDAV land in /dav (bind-mounted to ./consume), where
# the Paperless consumer picks them up automatically.
FROM httpd:2.4.67-alpine

# openssl: used by the entrypoint to hash the basic-auth password.
# apr-util-dbm_gdbm: DBM backend used by mod_dav's lock database.
RUN apk add --no-cache openssl apr-util-dbm_gdbm

# Enable the modules WebDAV + basic auth need, run as uid/gid 1000 so files
# written into the consume folder are owned by the host user, and load the
# WebDAV vhost config.
RUN sed -i \
        -e 's/#LoadModule dav_module/LoadModule dav_module/' \
        -e 's/#LoadModule dav_fs_module/LoadModule dav_fs_module/' \
        -e 's/#LoadModule auth_basic_module/LoadModule auth_basic_module/' \
        -e 's/#LoadModule authn_file_module/LoadModule authn_file_module/' \
        -e 's/#LoadModule authz_user_module/LoadModule authz_user_module/' \
        /usr/local/apache2/conf/httpd.conf \
 && sed -i \
        -e 's/^User www-data/User #1000/' \
        -e 's/^Group www-data/Group #1000/' \
        /usr/local/apache2/conf/httpd.conf \
 && echo "Include conf/extra/webdav.conf" >> /usr/local/apache2/conf/httpd.conf \
 && mkdir -p /dav

COPY webdav.conf /usr/local/apache2/conf/extra/webdav.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
CMD ["httpd-foreground"]
