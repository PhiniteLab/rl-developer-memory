# Compatibility

## Supported environments

Officially documented environments:
- Linux
- WSL 2

## Python support

The package requires:
- Python 3.10+

CI currently targets Python 3.12 for the main quality workflow, while package metadata includes 3.10 through 3.12.

## Filesystem guidance

Recommended:
- keep the active SQLite database on the local Linux or WSL filesystem
- use mirrored backup targets for copies only

Avoid:
- placing the active DB under `/mnt/c/...`
- treating cloud-sync folders as the live SQLite path

## Native Windows

Native Windows without WSL is not the documented target.
Some lifecycle and operational assumptions are Linux/WSL-oriented.

## Cron and service tooling

The backup helper and some operational examples assume standard Linux/WSL shell tooling.
If your environment does not support cron or `systemctl`, use `SKIP_CRON_INSTALL=1` and configure scheduling manually.
