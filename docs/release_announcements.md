# Release announcements

Status: canonical. How testers hear what is new in each build: email from the
server, and WhatsApp texts for the channel and the testers' broadcast list.

## The flow

1. **Every upload to internal testing** (`ship.yml`, Android job). The merged
   pull requests since the build closed testers hold
   (`scripts/release_changes.py`, from the versionCode Play reports for the
   alpha track) go to `POST /api/v1/releases/draft`. The server drops changes
   testers never see (CI, scripts, docs, tests, migrations, website, admin),
   asks Gemini for at most five plain lines under the house style
   (`astrospace/agents/style.py`), and queues a **team preview email**: the
   reader email as it would go out, the WhatsApp channel post, the broadcast
   message and the Play "What's new" text. The same plain lines become the
   internal track's "What's new". The draft is kept as the run artifact
   `release-notes-<versionCode>` for 90 days. Nothing reaches readers.
2. **"Broadcast update"** (Hawk's word, in the project). A thread runs
   *Actions › Announce* on main (`announce.yml`). It announces the build on
   closed testing, or first releases a newer one there when
   `promote_to_closed` is ticked (that also needs Hawk's word). It uses the
   previewed draft unless given its own notes, and calls
   `POST /api/v1/releases/announce`, which queues one email per reader with
   **tips and reminders** email on, and a team email with the WhatsApp texts.
   The run summary shows the texts too.
   **Every update carries a poster** (Hawk, 2026-10-27). Make it first: a
   1080x1440 picture in the brand style (template in the project files,
   `marketing/release-announcements/`), saved as a JPEG under
   `ui/public/email/updates/` and merged, so the app serves it. Then run
   Announce with `poster` set to its path (`/email/updates/<name>.jpg`): the
   reader email opens with it. Only pictures under `/email/` on the app's own
   site are allowed in an email.
3. **WhatsApp.** The thread sends the channel post and broadcast message (and
   a poster, when there is one) to the coordinator, which passes them to the
   thread that drives WhatsApp Web in Hawk's Chrome. That thread posts only
   after Hawk types yes there.

## Rules the code enforces

- Reader emails ride on `tips_email`, which readers turned on for "a feature
  worth trying". Consent is re-checked at send time, and the footer and
  `List-Unsubscribe` are the usual ones. One email per reader per build
  (`release_email:<user>:<versionCode>`), sent between 9 am and 8 pm their
  time, otherwise at 10 am.
- Every line is checked: under 120 characters, no prices, money, plans,
  links, website, `/buy`, internal test link or developer words. A model line
  that breaks a rule drops the whole model draft for tidied pull-request
  titles; a hand-written note that breaks one is refused (422).
- Posts carry the Play Store listing link, never the internal test link, and
  name a reply route (asksiddha@3senses.design).
- Only the `github-deployer` service account can call the routes: the
  workflows mint a Google ID token for it through Workload Identity
  Federation (audience: the Cloud Run URL), and the API verifies it. No shared
  secret. Override with `RELEASE_CALLER` / `RELEASE_TOKEN_AUDIENCE` only if
  the account or URL changes.
- Team emails go to `OWNER_ALERT_EMAILS` on the notifications job, like the
  team alerts.

## Why WhatsApp is not sent from code

WhatsApp Channels and broadcast lists in the Business app have no API. Sending
from code needs the WhatsApp Business Platform through a provider (AiSensy,
Interakt, Gupshup: a monthly plan from about ₹999, about ₹0.9 + GST per
marketing message, Meta business verification, pre-approved templates, and
nothing goes to the channel even then). It can share the Ask Siddha number
(coexistence). That waits for public launch; until then the free route is the
browser thread above.

A broadcast list reaches only people who have saved the Ask Siddha number, and
needs their phone numbers, which the app does not hold (testers are known by
Gmail). Hawk collects those.
