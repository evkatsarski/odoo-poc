#!/usr/bin/env bash
# Disposable Odoo 20 database for leather_inspection.
# Community source and the licensed Enterprise addons stay outside this repository.
#
# Required:
#   ODOO_BIN          python odoo-bin (default: /opt/odoo-venv/bin/python /opt/odoo/odoo-bin)
#   ENTERPRISE_ADDONS directory that contains the quality_control addon
# Optional:
#   COMMUNITY_ADDONS  default /opt/odoo/addons,/opt/odoo/odoo/addons
#   CUSTOM_ADDONS     default: this repo
#   DB_NAME           default leather_proto
#   HTTP_PORT         default 8069
#   DATA_DIR          default /opt/odoo-data
#
# PostgreSQL local peer authentication: run this as the OS role that owns the database.
# --without-demo is a boolean. Do not pass --without-demo=all (invalid since Odoo 19).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMMUNITY_ADDONS="${COMMUNITY_ADDONS:-/opt/odoo/addons,/opt/odoo/odoo/addons}"
CUSTOM_ADDONS="${CUSTOM_ADDONS:-$ROOT}"
ENTERPRISE_ADDONS="${ENTERPRISE_ADDONS:-}"
DB_NAME="${DB_NAME:-leather_proto}"
HTTP_PORT="${HTTP_PORT:-8069}"
DATA_DIR="${DATA_DIR:-/opt/odoo-data}"
PYTHON="${PYTHON:-/opt/odoo-venv/bin/python}"
ODOO_BIN="${ODOO_BIN:-/opt/odoo/odoo-bin}"

if [[ -z "$ENTERPRISE_ADDONS" || ! -d "$ENTERPRISE_ADDONS/quality_control" ]]; then
  echo "ENTERPRISE_ADDONS must be the licensed Odoo 20 Enterprise addons directory." >&2
  echo "quality_control was not found. The addon cannot be installed from Community alone." >&2
  echo "Example: ENTERPRISE_ADDONS=/opt/odoo-enterprise $0" >&2
  exit 2
fi

mkdir -p "$DATA_DIR"
ADDONS_PATH="${COMMUNITY_ADDONS},${ENTERPRISE_ADDONS},${CUSTOM_ADDONS}"

"$PYTHON" "$ODOO_BIN" \
  --addons-path="$ADDONS_PATH" \
  --data-dir="$DATA_DIR" \
  --http-port="$HTTP_PORT" \
  --without-demo \
  --stop-after-init \
  -d "$DB_NAME" \
  -i leather_inspection,point_of_sale \
  --load-language=en_US

echo "Installed leather_inspection and point_of_sale on ${DB_NAME}."
echo "Start the server with the same addons path, without --stop-after-init."
echo "Demo inspection users (created by the addon, password leather-demo):"
echo "  leather.entry.a  leather.entry.b  leather.operator  leather.admin"
echo "Database admin login is admin / admin on a database created from stock Odoo data."
