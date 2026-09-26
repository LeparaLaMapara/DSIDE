# The South African runner

SASSA and the Department of Water and Sanitation only answer South African
addresses. GitHub's own machines are in the United States and Europe, so they
are refused. This folder turns one small machine in South Africa into a GitHub
runner that fetches only those two sources, every Monday
(`.github/workflows/za-sources.yml`).

## What you need

- Any always-on machine on a South African internet connection: a Raspberry
  Pi 4 or 5 (64-bit Raspberry Pi OS), an old laptop or a mini PC with Ubuntu.
- Python 3.11 or newer and git (Raspberry Pi OS and Ubuntu 24.04 have both).
- About 2 GB of free disk space.

It uses very little: one job a week of about ten minutes.

## Set it up (once)

1. On any computer with the GitHub CLI logged in as an admin of the repo, make
   a registration token (it is valid for one hour):

       gh api -X POST repos/ubunye-ai-ecosystems/masepala/actions/runners/registration-token -q .token

2. On the South African machine:

       curl -fsSL https://raw.githubusercontent.com/ubunye-ai-ecosystems/masepala/master/za-runner/setup.sh -o setup.sh
       bash setup.sh <the token>

   The script installs GitHub's runner in `~/masepala-runner`, registers it
   with the label `za`, and starts it as a service so it comes back after a
   restart.

3. Check it on GitHub: Settings, Actions, Runners shows `masepala-za` as Idle.
   Then start the job once by hand:

       gh workflow run za-sources.yml -R ubunye-ai-ecosystems/masepala

## Safety

A runner on a public repository runs whatever job reaches it. So:

- `za-sources.yml` only runs on a schedule or when started by a maintainer,
  never on a pull request. Keep it that way.
- The repository requires approval before workflows from outside contributors
  run at all.
- Use a machine that holds nothing private, logged in as an ordinary user.

## If it is off

Nothing breaks. The Monday job waits for it, and the quarterly refresh uses
the copies it already has; `/status` shows how old they are. To remove it:
`cd ~/masepala-runner && sudo ./svc.sh uninstall && ./config.sh remove --token <a removal token>`.
