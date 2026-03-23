#!/usr/bin/env bash
set -euo pipefail
umask 022

REPO_URL="${LCARS_REPO_URL:-https://github.com/BigPattyOG/lcars-dev.git}"
INSTALL_ROOT="${LCARS_INSTALL_ROOT:-/opt/lcars}"
APP_ROOT="${INSTALL_ROOT}/app"
VENV_ROOT="${INSTALL_ROOT}/venv"
ENV_PATH="${INSTALL_ROOT}/.env"
PUBLIC_ENV_PATH="${INSTALL_ROOT}/public.env"
SERVICE_NAME="${LCARS_SERVICE_NAME:-lcars.service}"
SERVICE_USER="${LCARS_SERVICE_USER:-lcars}"
MARKER_PATH="${INSTALL_ROOT}/systemd-managed"
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

LOG_FILE="$(mktemp /tmp/lcars-install.XXXXXX.log)"
STEP_INDEX=0
TOTAL_STEPS=10

line() {
    printf '%s\n' "============================================================"
}

banner() {
    line
    printf '%sLCARS SYSTEM INITIALIZATION%s\n' "${COLOR_ORANGE}" "${COLOR_RESET}"
    printf '%sStructured installation and service activation sequence.%s\n' \
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
        fail "Run this installer with sudo or as root."
    fi
}

ensure_command() {
    if command -v "$1" >/dev/null 2>&1; then
        return
    fi
    fail "Missing required command: $1"
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

install_packages() {
    step "Verifying host dependencies"
    if command -v apt-get >/dev/null 2>&1; then
        run_logged "Refreshing apt package metadata" apt-get update
        run_logged \
            "Installing git and Python runtime packages" \
            env DEBIAN_FRONTEND=noninteractive \
            apt-get install -y git python3 python3-venv python3-pip
        return
    fi

    if command -v dnf >/dev/null 2>&1; then
        run_logged \
            "Installing git and Python runtime packages" \
            dnf install -y git python3 python3-pip
        return
    fi

    if command -v yum >/dev/null 2>&1; then
        run_logged \
            "Installing git and Python runtime packages" \
            yum install -y git python3 python3-pip
        return
    fi

    ensure_command git
    ensure_command python3
    ok "Host dependencies already available."
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
    step "Preparing LCARS service account"
    if id -u "${SERVICE_USER}" >/dev/null 2>&1; then
        ok "Service account ${SERVICE_USER} already present."
        return
    fi

    local shell_path="/usr/sbin/nologin"
    if [[ ! -x "${shell_path}" ]]; then
        shell_path="/usr/bin/false"
    fi
    run_logged \
        "Creating ${SERVICE_USER} service account" \
        useradd --system --home "${INSTALL_ROOT}" --create-home --shell "${shell_path}" "${SERVICE_USER}"
}

sync_repository() {
    step "Syncing LCARS repository"
    mkdir -p "${INSTALL_ROOT}"

    if [[ -d "${APP_ROOT}/.git" ]]; then
        run_logged "Fetching latest LCARS repository state" git -C "${APP_ROOT}" fetch --prune origin
        run_logged "Checking out LCARS main branch" git -C "${APP_ROOT}" checkout main
        run_logged "Resetting local repository to origin/main" git -C "${APP_ROOT}" reset --hard origin/main
    else
        rm -rf "${APP_ROOT}"
        run_logged "Cloning LCARS repository" git clone --branch main "${REPO_URL}" "${APP_ROOT}"
    fi
}

build_virtualenv() {
    step "Building LCARS runtime"
    run_logged "Creating LCARS virtual environment" python3 -m venv "${VENV_ROOT}"
    run_logged "Upgrading pip toolchain" "${VENV_ROOT}/bin/python" -m pip install --upgrade pip setuptools wheel
    run_logged "Installing LCARS package into virtual environment" "${VENV_ROOT}/bin/python" -m pip install "${APP_ROOT}"
}

write_environment() {
    local discord_token="$1"
    local environment_name="$2"

    step "Writing LCARS configuration"
    mkdir -p "${INSTALL_ROOT}"
    cat > "${ENV_PATH}" <<EOF
# LCARS runtime configuration
LCARS_ENVIRONMENT=${environment_name}
LCARS_DISCORD_TOKEN=${discord_token}
LCARS_LOG_LEVEL=INFO
LCARS_SYSTEMD_MANAGED=1
LCARS_SERVICE_NAME=${SERVICE_NAME}
EOF
    cat > "${PUBLIC_ENV_PATH}" <<EOF
# LCARS public runtime profile
LCARS_ENVIRONMENT=${environment_name}
LCARS_TOKEN_CONFIGURED=1
EOF
    : > "${MARKER_PATH}"
    ok "Secret runtime profile written to ${ENV_PATH}."
    ok "Public runtime profile written to ${PUBLIC_ENV_PATH}."
}

write_service_unit() {
    step "Registering LCARS system service"
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
    ok "systemd unit written to ${UNIT_PATH}."
}

write_cli_wrapper() {
    step "Publishing LCARS command"
    cat > "${BIN_LINK}" <<EOF
#!/usr/bin/env bash
export LCARS_INSTALL_ROOT="${INSTALL_ROOT}"
export LCARS_RUNTIME_ROOT="${INSTALL_ROOT}"
export LCARS_ENV_PATH="${ENV_PATH}"
export LCARS_PUBLIC_ENV_PATH="${PUBLIC_ENV_PATH}"
export LCARS_STATE_DIR="${INSTALL_ROOT}/state"
export LCARS_LOG_DIR="${INSTALL_ROOT}/logs"
export LCARS_REPO_ROOT="${APP_ROOT}"
export LCARS_SYSTEMD_MANAGED=1
export LCARS_SERVICE_NAME="${SERVICE_NAME}"
exec "${VENV_ROOT}/bin/python" -m lcars.cli.main "\$@"
EOF
    chmod 755 "${BIN_LINK}"
    ok "Global LCARS command published at ${BIN_LINK}."
}

activate_service() {
    step "Activating LCARS service"
    run_logged "Reloading systemd daemon" systemctl daemon-reload
    run_logged "Enabling and starting ${SERVICE_NAME}" systemctl enable --now "${SERVICE_NAME}"
}

fix_permissions() {
    step "Applying filesystem permissions"
    mkdir -p "${INSTALL_ROOT}/state" "${INSTALL_ROOT}/logs"
    chown root:root "${INSTALL_ROOT}"
    chown -R root:root "${APP_ROOT}" "${VENV_ROOT}"
    chown -R "${SERVICE_USER}:${SERVICE_USER}" "${INSTALL_ROOT}/state" "${INSTALL_ROOT}/logs"
    chown root:"${SERVICE_USER}" "${ENV_PATH}" "${MARKER_PATH}"
    chown root:root "${PUBLIC_ENV_PATH}"

    chmod 755 "${INSTALL_ROOT}" "${APP_ROOT}" "${VENV_ROOT}" \
        "${INSTALL_ROOT}/state" "${INSTALL_ROOT}/logs"
    chmod -R a+rX "${APP_ROOT}" "${VENV_ROOT}"
    chmod 640 "${ENV_PATH}"
    chmod 644 "${PUBLIC_ENV_PATH}"
    chmod 644 "${MARKER_PATH}"
    ok "Filesystem ownership and execution permissions normalized."
}

main() {
    need_root
    banner
    install_packages

    local discord_token
    local environment_name
    step "Collecting runtime inputs"
    discord_token="${LCARS_DISCORD_TOKEN:-$(prompt_secret "Discord bot token")}"
    [[ -n "${discord_token}" ]] || fail "Discord bot token is required."
    environment_name="${LCARS_ENVIRONMENT:-$(prompt_value "Environment" "production")}"
    environment_name="${environment_name^^}"
    ok "Runtime environment set to ${environment_name}."
    ok "Discord bot token captured."

    ensure_command systemctl
    ensure_service_user
    sync_repository
    build_virtualenv
    write_environment "${discord_token}" "${environment_name}"
    fix_permissions
    write_service_unit
    write_cli_wrapper
    activate_service

    line
    printf '%sLCARS initialization complete. System operational.%s\n' \
        "${COLOR_GREEN}" "${COLOR_RESET}"
    printf '%sStardate:%s %s\n' "${COLOR_PURPLE}" "${COLOR_RESET}" "2026.082.1"
    printf '%sEnvironment:%s %s\n' "${COLOR_PURPLE}" "${COLOR_RESET}" "${environment_name}"
    printf 'Command interface: %s\n' "${BIN_LINK}"
    printf 'Service: %s\n' "${SERVICE_NAME}"
    printf 'Installer log: %s\n' "${LOG_FILE}"
    line
}

main "$@"
