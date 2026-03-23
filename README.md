# LCARS

LCARS is a production-oriented command line and Discord control system built in
Python with Click, Rich, and psutil. The project exposes a structured LCARS
dashboard, a live monitoring console, an interactive installer, and a Discord
bot runtime controlled through the same service layer.

## Commands

- `lcars`
- `lcars help`
- `lcars motd`
- `lcars status`
- `lcars monitor`
- `lcars restart`
- `lcars shutdown`
- `lcars update`
- `lcars version`
- `lcars logs`
- `lcars doctor`
- `lcars install`

## Runtime

- Release metadata is stored statically in `lcars/version.json`.
- The installer writes configuration to `/opt/lcars/.env` by default.
- Runtime state and logs default to `/opt/lcars/state` and `/opt/lcars/logs`.
- Production installs use `systemd` service `lcars.service`.

## Deployment

Uninstall the current LCARS system:

```bash
curl -fsSL https://raw.githubusercontent.com/BigPattyOG/lcars-dev/main/scripts/uninstall.sh | sudo bash
```

Install the rebuilt LCARS system:

```bash
curl -fsSL https://raw.githubusercontent.com/BigPattyOG/lcars-dev/main/scripts/install.sh | sudo bash
```

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install ".[dev]"
black .
ruff check .
pytest
```
