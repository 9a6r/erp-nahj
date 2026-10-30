#!/bin/sh
set -eu
umask 0027
# Every service shares this volume. Avoid removing assets while another service
# is serving requests; only create the link once, tolerating a concurrent start.
assets=/home/frappe/frappe-bench/sites/assets
baked=/home/frappe/frappe-bench/assets
if [ ! -L "$assets" ]; then
    if [ -e "$assets" ]; then
        echo 'Existing assets directory needs operator review; refusing to remove it.' >&2
        exit 1
    fi
    ln -s "$baked" "$assets" 2>/dev/null || [ -L "$assets" ]
fi
[ "$(readlink "$assets")" = "$baked" ] || {
    echo 'Unexpected assets link; refusing to replace it.' >&2
    exit 1
}
exec "$@"
