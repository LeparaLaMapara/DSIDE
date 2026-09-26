#!/usr/bin/env bash
# Register this machine as Masepala's South African GitHub runner (label `za`).
#   bash setup.sh <registration token>     see za-runner/README.md for the token
set -euo pipefail
token="${1:?usage: bash setup.sh <registration token>}"
repo="https://github.com/ubunye-ai-ecosystems/masepala"
dir="$HOME/masepala-runner"

case "$(uname -m)" in
  x86_64) arch=x64 ;;
  aarch64|arm64) arch=arm64 ;;
  armv7l) arch=arm ;;
  *) echo "unsupported machine: $(uname -m)" >&2; exit 1 ;;
esac

command -v python3 >/dev/null || { echo "install python3 first" >&2; exit 1; }
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11 or newer is needed"'
python3 -m venv --help >/dev/null 2>&1 || { echo "install python3-venv first (sudo apt install python3-venv)" >&2; exit 1; }

# Are we really in South Africa? The whole point of this runner.
country="$(curl -fsS https://ipinfo.io/country || true)"
[ "$country" = "ZA" ] || echo "warning: this connection looks like '$country', not ZA; SASSA and DWS may refuse it"

version="$(curl -fsS https://api.github.com/repos/actions/runner/releases/latest | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"].lstrip("v"))')"
mkdir -p "$dir" && cd "$dir"
curl -fsSL -o runner.tar.gz "https://github.com/actions/runner/releases/download/v${version}/actions-runner-linux-${arch}-${version}.tar.gz"
tar xzf runner.tar.gz && rm runner.tar.gz

./config.sh --unattended --url "$repo" --token "$token" --name masepala-za --labels za --replace
sudo ./svc.sh install "$USER"
sudo ./svc.sh start
echo "Registered. GitHub, Settings, Actions, Runners should now show masepala-za as Idle."
