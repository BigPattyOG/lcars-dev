#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${LCARS_INSTALL_ROOT:-/opt/lcars}"
SERVICE_NAME="${LCARS_SERVICE_NAME:-lcars.service}"
SERVICE_USER="${LCARS_SERVICE_USER:-lcars}"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}"
BIN_LINK="/usr/local/bin/lcars"

LEGACY_PATHS=(
    "${INSTALL_ROOT}"
    "/opt/lcars-dev"
    "/opt/lcars-prod"
    "/root/lcars-dev"
    "/root/lcars-prod"
)

note() {
    printf '\n== %s ==\n' "$1"
}

need_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        printf 'Run this uninstall script with sudo or as root.\n' >&2
        exit 1
    fi
}

remove_path_if_present() {
    local target="$1"
    if [[ -e "${target}" ]]; then
        rm -rf "${target}"
    fi
}

main() {
    need_root

    note "Stopping LCARS services"
    if command -v systemctl >/dev/null 2>&1; then
        systemctl disable --now "${SERVICE_NAME}" 2>/dev/null || true
        systemctl daemon-reload 2>/dev/null || true
    fi

    note "Removing LCARS service files"
    rm -f "${UNIT_PATH}" "${BIN_LINK}"
    if command -v systemctl >/dev/null 2>&1; then
        systemctl daemon-reload 2>/dev/null || true
    fi

    note "Removing LCARS application data"
    for target in "${LEGACY_PATHS[@]}"; do
        remove_path_if_present "${target}"
    done

    for target in /home/*/lcars-dev /home/*/lcars-prod; do
        if [[ -e "${target}" ]]; then
            rm -rf "${target}"
        fi
    done

    note "Removing LCARS service account"
    if id -u "${SERVICE_USER}" >/dev/null 2>&1; then
        userdel "${SERVICE_USER}" 2>/dev/null || true
    fi

    note "Legacy LCARS uninstall complete."
}

main "$@"
