# Builds on the Mac mini (self-hosted runner)

Status: canonical. Where CI, Ship and the iOS launch check run, and how the
Mac mini is set up to run them for free once the repository is private.

## Why

A public repository builds free on GitHub's machines. A private one gets $12
of build time a month on GitHub Free ($18 on Pro), then pays $0.006 a Linux
minute and $0.062 a Mac minute. Measured over 16 to 29 October 2026 we used
about 19,000 Linux and 2,400 Mac minutes a month, about $260 at private
prices. Builds on a machine we own (a self-hosted runner) cost nothing and
do not touch the $12.

GitHub announced a $0.002 a minute fee for self-hosted runners in private
repositories for March 2026 and postponed it with no new date. If it comes
back, this setup would cost roughly $25 to $40 a month.

## The switch

Every job reads its machine from the repository variable `BUILD_RUNNER`
(Settings › Secrets and variables › Actions › Variables):

| `BUILD_RUNNER` | Linux jobs | Mac jobs (iOS) |
| --- | --- | --- |
| unset | `ubuntu-latest` (GitHub) | `macos-26` (GitHub) |
| `siddha-mac` | the Mac mini | the Mac mini |

Never set it while the repository is public: on a public repository anyone
can open a pull request, and the Mac would run its code. If the Mac is away
for days, delete the variable and builds go back to GitHub's machines, which
use the free $12 first and then stop at the $0 budget.

## What the workflows do differently on the Mac

- Postgres for the migration check is a plain `docker run` on port 55432
  (service containers exist only on Linux runners), and psql runs inside it.
- Docker images are built for `linux/amd64`, what Cloud Run runs, under
  Rosetta. The CI smoke test listens on port 18080.
- Xcode is the one the Mac has selected; the job only checks it is Xcode 26
  or newer (GitHub's image needs `sudo xcode-select`, the Mac has no sudo
  for jobs). The Mac mini had Xcode 27.1 on 2026-10-29.
- The App Store Connect key goes in the job's temporary folder, never
  `~/.appstoreconnect`, which holds the Mac's own keys. Provisioning profiles
  the job installs, the throwaway keychain, the Android upload key and
  `google-services.json` are removed at the end of every job.
- gcloud's sign-in lives in the job's temporary folder (`CLOUDSDK_CONFIG`),
  so the Mac's own `gcloud` account is never switched.
- The iOS launch check shuts its simulator down and copies only crash
  reports written during the run.
- One runner runs one job at a time, so a merge's CI and Ship queue behind
  each other. A second runner instance can be added later if that is slow.
- Playwright starts `ng serve` on port 4200; a dev server left running on
  the Mac on that port fails the e2e job.

## One-time Mac setup

1. **Stay awake.** System Settings › Energy: *Prevent automatic sleeping when
   the display is off*, *Wake for network access*, *Start up automatically
   after a power failure* on. Users & Groups: automatic login for the
   account the runner uses (the runner is a LaunchAgent and runs only while
   that account is logged in).
2. **Docker.** The Mac mini already has Docker Desktop (free for a studio
   under 250 people and $10M revenue). Settings › General: *Start Docker
   Desktop when you sign in* and *Use Rosetta for x86_64/amd64 emulation on
   Apple Silicon* on; Resources: 4 CPUs, 8 GB. Check:

   ```bash
   docker run --rm --platform linux/amd64 alpine uname -m   # x86_64
   docker run --rm alpine uname -m                          # aarch64
   ```

   Colima (`brew install colima`, `colima start --vm-type vz --vz-rosetta`)
   does the same on a Mac without Docker Desktop.
3. **The runner**, only after the repository is private. From a terminal
   where `brew`, `node` and `gh` (signed in as repos-3sds) are on the PATH,
   because the service keeps that PATH:

   ```bash
   mkdir -p ~/actions-runner && cd ~/actions-runner
   V=$(gh api repos/actions/runner/releases/latest --jq .tag_name | sed 's/^v//')
   curl -fsSLo runner.tgz "https://github.com/actions/runner/releases/download/v$V/actions-runner-osx-arm64-$V.tar.gz"
   tar xzf runner.tgz && rm runner.tgz
   TOKEN=$(gh api -X POST repos/repos-3sds/agentic-astrospace/actions/runners/registration-token --jq .token)
   ./config.sh --url https://github.com/repos-3sds/agentic-astrospace --token "$TOKEN" \
     --name siddha-mac --labels siddha-mac --work _work --unattended --replace
   echo "ANDROID_HOME=$HOME/Library/Android/sdk" >> .env
   ./svc.sh install && ./svc.sh start && ./svc.sh status
   ```

   It shows as *Idle* under Settings › Actions › Runners.
4. **Set `BUILD_RUNNER` = `siddha-mac`**, then *Actions › Ship › Run workflow*
   on main with *ship everything* ticked, and check the API deploy, the AAB
   and the TestFlight upload all ran on `siddha-mac`.

To stop: `cd ~/actions-runner && ./svc.sh stop && ./svc.sh uninstall`, then
remove the runner under Settings › Actions › Runners and delete the variable.

## Going private, in order

1. Merge the workflow change (it changes nothing while `BUILD_RUNNER` is unset).
2. Mac setup steps 1 and 2.
3. Settings › Pages: unpublish (the old `docs/index.html` page; asksiddha.app
   is on Firebase). Pages on a private repository needs Pro.
4. Settings › General › Danger Zone › Change visibility › Private.
5. Mac setup steps 3 and 4.
6. Billing and licensing › Budgets: Actions budget $0 with *stop usage* on.
