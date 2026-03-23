#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${LCARS_REPO_URL:-https://github.com/BigPattyOG/lcars-dev.git}"
INSTALL_ROOT="${LCARS_INSTALL_ROOT:-/opt/lcars}"
APP_ROOT="${INSTALL_ROOT}/app"
VENV_ROOT="${INSTALL_ROOT}/venv"
ENV_PATH="${INSTALL_ROOT}/.env"
SERVICE_NAME="${LCARS_SERVICE_NAME:-lcars.service}"
SERVICE_USER="${LCARS_SERVICE_USER:-lcars}"
MARKER_PATH="${INSTALL_ROOT}/systemd-managed"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}"
BIN_LINK="/usr/local/bin/lcars"

fail() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 1
}

note() {
    printf '\n== %s ==\n' "$1"
}

need_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        fail "Run this installer with sudo or as root."
    fi
}

ensure_command() {
    if command -v "$1" >/dev/null 2>&1; then
        return
    fi
    fail "Missing required command: $1"
}

install_packages() {
    if command -v apt-get >/dev/null 2>&1; then
        note "Installing system dependencies"
        apt-get update
        DEBIAN_FRONTEND=noninteractive apt-get install -y git python3 python3-venv python3-pip
        return
    fi

    if command -v dnf >/dev/null 2>&1; then
        note "Installing system dependencies"
        dnf install -y git python3 python3-pip
        return
    fi

    if command -v yum >/dev/null 2>&1; then
        note "Installing system dependencies"
        yum install -y git python3 python3-pip
        return
    fi

    ensure_command git
    ensure_command python3
}

prompt_value() {
    local prompt_text="$1"
    local default_value="${2:-}"
    local response

    if [[ -n "${default_value}" ]]; then
        printf '%s [%s]: ' "${prompt_text}" "${default_value}" > /dev/tty
    else
        printf '%s: ' "${prompt_text}" > /dev/tty
    fi
    IFS= read -r response < /dev/tty
    if [[ -z "${response}" ]]; then
        response="${default_value}"
    fi
    printf '%s' "${response}"
}

prompt_secret() {
    local prompt_text="$1"
    local response

    printf '%s: ' "${prompt_text}" > /dev/tty
    stty -echo < /dev/tty
    IFS= read -r response < /dev/tty
    stty echo < /dev/tty
    printf '\n' > /dev/tty
    printf '%s' "${response}"
}

ensure_service_user() {
    if id -u "${SERVICE_USER}" >/dev/null 2>&1; then
        return
    fi

    local shell_path="/usr/sbin/nologin"
    if [[ ! -x "${shell_path}" ]]; then
        shell_path="/usr/bin/false"
    fi
    useradd --system --home "${INSTALL_ROOT}" --create-home --shell "${shell_path}" "${SERVICE_USER}"
}

sync_repository() {
    note "Syncing LCARS repository"
    mkdir -p "${INSTALL_ROOT}"

    if [[ -d "${APP_ROOT}/.git" ]]; then
        git -C "${APP_ROOT}" fetch --prune origin
        git -C "${APP_ROOT}" checkout main
        git -C "${APP_ROOT}" reset --hard origin/main
    else
        rm -rf "${APP_ROOT}"
        git clone --branch main "${REPO_URL}" "${APP_ROOT}"
    fi
}

build_virtualenv() {
    note "Building LCARS runtime"
    python3 -m venv "${VENV_ROOT}"
    "${VENV_ROOT}/bin/python" -m pip install --upgrade pip setuptools wheel
    "${VENV_ROOT}/bin/python" -m pip install "${APP_ROOT}"
}

write_environment() {
    local discord_token="$1"
    local environment_name="$2"

    note "Writing LCARS configuration"
    mkdir -p "${INSTALL_ROOT}"
    cat > "${ENV_PATH}" <<EOF
# LCARS runtime configuration
LCARS_ENVIRONMENT=${environment_name}
LCARS_DISCORD_TOKEN=${discord_token}
LCARS_LOG_LEVEL=INFO
LCARS_SYSTEMD_MANAGED=1
LCARS_SERVICE_NAME=${SERVICE_NAME}
EOF
    : > "${MARKER_PATH}"
}

write_service_unit() {
    note "Registering LCARS system service"
    cat > "${UNIT_PATH}" <<EOF
[Unit]
Description=LCARS Discord Bot Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${APP_ROOT}
Environment=LCARS_INSTALL_ROOT=${INSTALL_ROOT}
Environment=LCARS_RUNTIME_ROOT=${INSTALL_ROOT}
Environment=LCARS_ENV_PATH=${ENV_PATH}
Environment=LCARS_STATE_DIR=${INSTALL_ROOT}/state
Environment=LCARS_LOG_DIR=${INSTALL_ROOT}/logs
Environment=LCARS_REPO_ROOT=${APP_ROOT}
Environment=LCARS_SYSTEMD_MANAGED=1
Environment=LCARS_SERVICE_NAME=${SERVICE_NAME}
ExecStart=${VENV_ROOT}/bin/python -m lcars.systems.bot_runtime
Restart=always
RestartSec=5
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
EOF
}

write_cli_wrapper() {
    note "Publishing LCARS command"
    cat > "${BIN_LINK}" <<EOF
#!/usr/bin/env bash
export LCARS_INSTALL_ROOT="${INSTALL_ROOT}"
export LCARS_RUNTIME_ROOT="${INSTALL_ROOT}"
export LCARS_ENV_PATH="${ENV_PATH}"
export LCARS_STATE_DIR="${INSTALL_ROOT}/state"
export LCARS_LOG_DIR="${INSTALL_ROOT}/logs"
export LCARS_REPO_ROOT="${APP_ROOT}"
export LCARS_SYSTEMD_MANAGED=1
export LCARS_SERVICE_NAME="${SERVICE_NAME}"
exec "${VENV_ROOT}/bin/python" -m lcars.cli.main "\$@"
EOF
    chmod 755 "${BIN_LINK}"
}

activate_service() {
    note "Activating LCARS service"
    systemctl daemon-reload
    systemctl enable --now "${SERVICE_NAME}"
}

fix_permissions() {
    mkdir -p "${INSTALL_ROOT}/state" "${INSTALL_ROOT}/logs"
    chown root:root "${INSTALL_ROOT}"
    chown -R root:root "${APP_ROOT}" "${VENV_ROOT}"
    chown -R "${SERVICE_USER}:${SERVICE_USER}" "${INSTALL_ROOT}/state" "${INSTALL_ROOT}/logs"
    chown root:"${SERVICE_USER}" "${ENV_PATH}" "${MARKER_PATH}"

    chmod 755 "${INSTALL_ROOT}" "${APP_ROOT}" "${VENV_ROOT}" \
        "${INSTALL_ROOT}/state" "${INSTALL_ROOT}/logs"
    chmod -R a+rX "${APP_ROOT}" "${VENV_ROOT}"
    chmod 640 "${ENV_PATH}"
    chmod 644 "${MARKER_PATH}"
}

main() {
    need_root
    install_packages

    local discord_token
    local environment_name
    discord_token="$(prompt_secret "Discord bot token")"
    [[ -n "${discord_token}" ]] || fail "Discord bot token is required."
    environment_name="$(prompt_value "Environment" "production")"
    environment_name="${environment_name^^}"

    ensure_command systemctl
    ensure_service_user
    sync_repository
    build_virtualenv
    write_environment "${discord_token}" "${environment_name}"
    fix_permissions
    write_service_unit
    write_cli_wrapper
    activate_service

    note "LCARS initialization complete. System operational."
    printf 'Command interface: %s\n' "${BIN_LINK}"
    printf 'Service: %s\n' "${SERVICE_NAME}"
}

main "$@"
