# Stable server image

## Payments candidate 0.3.2

`build_candidate.py` adds the official Payments app at the commit and source
archive digest in `payments-lock.json` to the verified, published 0.3.1 image.
It installs the versions in `payments-constraints.txt`, runs `pip check`, records
the installed dependencies, and bakes the supported application inventory into
`/home/frappe/nahj-apps.json`. This inventory also identifies the single legacy
image eligible for restoration into a separate new site.

`payments_localization.py` validates and compiles 150 Arabic messages and wraps
three existing Paytm template strings in gettext. The inventory records the
catalogue hash and the original/localized template hashes. Provider payment
logic remains from the pinned official source. A complete static catalogue does
not establish that every externally hosted checkout page is translated.

The candidate workflow builds the archive **once** and runs the native Arch/Zen,
real ERP, independent recovery, legacy migration and original module suites
against that exact archive. Publication promotes those tested bytes; dependency
resolution is not repeated. Constraints pin package versions, but are not a
claim that arbitrary future rebuilds will be byte-identical. After publication,
`tests/build-ci-image.sh` downloads and verifies the published archive for later
acceptance runs. No production data or site credentials are included.

## Reproducing the retained 0.3.1 base

The desktop's managed server is based on the official Frappe ERPNext image. The
upstream source versions, commits and amd64 manifest digest are in `upstream.json`.
The image contains the complete upstream ERPNext/Frappe applications; the overlay
adds Nahj banking assets, the language endpoint, a non-destructive entrypoint and
the external MariaDB TLS preflight, complete Arabic catalogues and print-language
amount-in-words rendering. No company records or site credentials are
included.

Build the banking assets, then use Google's open-source
[crane](https://github.com/google/go-containerregistry) to build the server archive:

```sh
cd banking
yarn install --frozen-lockfile
yarn build
cd ..
python3 -m venv work/build-env
work/build-env/bin/pip install --require-hashes -r desktop/server-image/requirements.txt
work/build-env/bin/python desktop/server-image/build.py --crane crane \
  --work-dir ./work/image-build \
  --output ./work/nahj-server-0.3.1-rc1-amd64.tar.gz
```

The builder exports only the digest-pinned upstream image over verified TLS. It
replaces overlay paths, preserves the original runtime configuration and writes
a Docker archive with one layer, plus JSON containing its SHA256, image ID and
size. This avoids the repeated full filesystem copies that Docker's VFS driver
makes for upstream layers. Allow at least 12 GiB free for building; runtime data,
engine storage and backups require additional space. Rootless Podman with overlay
storage is the intended Arch runtime.

Before a release, compare the output metadata with
`../nahj_desktop/server_release.json`, import the archive and complete the
acceptance checks. Rebuilding source does not automatically publish a release or
change the desktop's trusted image. `published` must remain false until the exact
archive is available at its recorded public URL and has passed release validation.

The old 0.3.0 archive is based on development versions. Do not reuse its hash, tag
or database volumes for the stable runtime. An ERPNext 17 database must not be
downgraded to 16; retain it and plan a supported data migration separately.
