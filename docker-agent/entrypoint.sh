#!/bin/bash
# Materializes the opencode config into the writable state volume on every
# start (idempotent - the volume is empty on first boot, and this just
# re-syncs it on later boots too, so config edits in the image take effect
# on the next `docker compose up` without needing to wipe the volume).
set -euo pipefail

mkdir -p /root/.config/opencode
cp /opt/opencode-config/opencode.json /root/.config/opencode/opencode.json

exec "$@"
