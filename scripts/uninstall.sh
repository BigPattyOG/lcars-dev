#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${LCARS_INSTALL_ROOT:-/opt/lcars}"
SERVICE_NAME="${LCARS_SERVICE_NAME:-lcars.service}"
SERVICE_USER="${LCARS_SERVICE_USER:-lcars}"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}"
BIN_LINK="/usr/local/bin/lcars"

if [[ -t 1 ]]; then
    COLOR_ORANGE=$'\033[38;5;215m'
    COLOR_PURPLE=$'\033[38;5;141m'
    COLOR_CYAN=$'\033[38;5;87m'
    COLOR_GREEN=$'\033[38;5;78m'
    COLOR_RED=$'\033[38;5;203m'
    COLOR_RESET=$'\033[0m'
else
    COLOR_ORANGE=""
    COLOR_PURPLE=""
    COLOR_CYAN=""
    COLOR_GREEN=""
    COLOR_RED=""
    COLOR_RESET=""
fi

LOG_FILE="$(mktemp /tmp/lcars-uninstall.XXXXXX.log)"
STEP_INDEX=0
TOTAL_STEPS=4

line() {
    printf '%s\n' "============================================================"
}

banner() {
    line
    printf '%sLCARS SYSTEM DECOMMISSION%s\n' "${COLOR_ORANGE}" "${COLOR_RESET}"
    printf '%sRemoving LCARS runtime, service, and command interface.%s\n' \
        "${COLOR_CYAN}" "${COLOR_RESET}"
    line
}

step() {
    STEP_INDEX=$((STEP_INDEX + 1))
    printf '\n%s[%d/%d]%s %s%s%s\n' \
        "${COLOR_PURPLE}" "${STEP_INDEX}" "${TOTAL_STEPS}" "${COLOR_RESET}" \
        "${COLOR_ORANGE}" "$1" "${COLOR_RESET}"
}

detail() {
    printf '  %s%s%s\n' "${COLOR_CYAN}" "$1" "${COLOR_RESET}"
}

ok() {
    printf '  %sOK%s %s\n' "${COLOR_GREEN}" "${COLOR_RESET}" "$1"
}

warn() {
    printf '  %sWARN%s %s\n' "${COLOR_ORANGE}" "${COLOR_RESET}" "$1"
}

fail() {
    printf '\n%sFAULT%s %s\n' "${COLOR_RED}" "${COLOR_RESET}" "$1" >&2
    printf 'Installer log: %s\n' "${LOG_FILE}" >&2
    tail -n 40 "${LOG_FILE}" >&2 || true
    exit 1
}

need_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        fail "Run this uninstaller with sudo or as root."
    fi
}

confirm_removal() {
    if [[ "${LCARS_UNINSTALL_FORCE:-0}" == "1" ]]; then
        return
    fi
    if [[ ! -t 0 ]]; then
        fail "Set LCARS_UNINSTALL_FORCE=1 for non-interactive removal."
    fi

    local response
    printf 'Proceed with LCARS removal from %s? [y/N]: ' "${INSTALL_ROOT}" > /dev/tty
    IFS= read -r response < /dev/tty
    case "${response}" in
        y|Y|yes|YES) ;;
        *) fail "Removal cancelled." ;;
    esac
}

run_logged() {
    local label="$1"
    shift
    detail "${label}"
    if "$@" >>"${LOG_FILE}" 2>&1; then
        ok "${label}"
        return
    fi
    fail "${label}"
}

remove_if_present() {
    local target="$1"
    if [[ -e "${target}" ]]; then
        run_logged "Removing ${target}" rm -rf "${target}"
    else
        warn "${target} not present."
    fi
}

main() {
    need_root
    banner
    confirm_removal

    step "Stopping LCARS service"
    if command -v systemctl >/dev/null 2>&1; then
        if systemctl cat "${SERVICE_NAME}" >>"${LOG_FILE}" 2>&1; then
            run_logged "Disabling ${SERVICE_NAME}" systemctl disable --now "${SERVICE_NAME}"
        else
            warn "Service ${SERVICE_NAME} not installed."
        fi
    else
        warn "systemctl not available; skipping service stop."
    fi

    step "Removing system integration"
    remove_if_present "${UNIT_PATH}"
    remove_if_present "${BIN_LINK}"
    if command -v systemctl >/dev/null 2>&1; then
        run_logged "Reloading systemd daemon" systemctl daemon-reload
    fi

    step "Removing LCARS runtime"
    remove_if_present "${INSTALL_ROOT}"

    step "Removing LCARS service account"
    if id -u "${SERVICE_USER}" >/dev/null 2>&1; then
        run_logged "Deleting ${SERVICE_USER} account" userdel "${SERVICE_USER}"
    else
        warn "Service account ${SERVICE_USER} not present."
    fi

    printf '\n%sLCARS uninstall complete.%s\n' "${COLOR_GREEN}" "${COLOR_RESET}"
    printf 'Log file: %s\n' "${LOG_FILE}"
}

main "$@"
