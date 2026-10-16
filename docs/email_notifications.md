# Email notifications

Status: canonical. How the app emails readers, what it needs in production, and what comes next.

## What is sent

| Email | Category | When (reader's local time) | Source |
| --- | --- | --- | --- |
| Daily reading | `daily_email` | 06:30 (or their `preferred_time`) | the brief the worker already stored for their own profile; skipped if not written by 11:00 |
| Moon and festival days | `festival_email` | 18:00 the evening before | full and new moons (lunar day at sunrise) and pan-India festivals at their place |
| Weekly outlook | `weekly_email` | Monday 07:00 | the period agent's weekly reading, with a plain-words style note; written from 18:00 Sunday, given up at 11:00 Monday, 6 per worker run |
| Monthly outlook | `monthly_email` | the 1st, 07:30 | the same, monthly |
| Learn your chart | `lessons_email` | 08:00, every 3 days, 8 in all | fixed lessons filled in from the reader's own chart (no model call); the first a day after they agree |
| Tips: back after a while | `tips_email` | 10:00 | after 14 days without opening the app (devices and push tokens), at most monthly: what is coming up at their place |
| Tips: compatibility | `tips_email` | 10:00, once | a week after sign-up, only if they have just their own profile |
| Welcome | `system` | once, when they first turn an email on | what they chose; asks for a birth time when theirs isn't exact |
| Team alert | `owner_alert` | within one worker run | a reader's first sign-in, and their first Ask question; to `OWNER_ALERT_EMAILS`, never to the reader |

The team alert (`astrospace/notifications/owner_alerts.py`) is for the friends-and-family test.
It is off until `OWNER_ALERT_EMAILS` (comma-separated) is set on the notifications job, looks
back two hours only, so switching it on mails no history, and never includes what was asked.

Every category starts **off** for a reader with no choice on record. The Register screen has an
email box, ticked by default; readers who never saw it (Google from the Sign in tab, a magic link)
see the same box on Birth Details. If it stays ticked, the end of onboarding calls
`POST /api/v1/me/email/defaults`, which turns every category on, once, and records
`consented_at` and `consent_source` on `email_recipients`. It does nothing for a reader who has
already set any email choice. Readers who signed up earlier keep what they chose. Any category
can be changed in Settings › Notifications › Email (`/api/v1/me/email`), and consent is checked
again at send time.

Open question for launch: whether a pre-ticked box is valid consent under India's DPDP Act. It
goes with the legal text for the lawyer's read; unticking the default is a one-line change in
`mobile-auth.component.ts` and `birth-details.component.ts`.

Code: `astrospace/notifications/email.py` (transport, signed links, layout),
`astrospace/notifications/email_jobs.py` (schedulers, delivery),
`astrospace/notifications/email_series.py` (outlooks, lessons, tips),
`astrospace/api/email_routes.py` (settings, unsubscribe, webhook). The worker runs them
beside the push schedulers on the same `notification_jobs` queue; an email job has
`payload.channel = "email"`.

## Rules the code enforces

- Every non-account email has `List-Unsubscribe` and `List-Unsubscribe-Post` (RFC 8058) and
  footer links for "stop these" and "stop all". Gmail and Yahoo require both of bulk senders.
- The unsubscribe GET only shows a confirm button; link scanners open every link.
- A hard bounce or spam complaint (Resend webhook) suppresses the address for good.
  A changed sign-in address clears it.
- All copy is escaped once in `render`; agent text is never trusted as markup.
- Copy follows `design-thinking/design_principles.md`: no fear, no verdicts, and every
  festival email says family and temple calendars may mark the day differently.

## Production setup

Sending is from `Siddha <asksiddha@3senses.design>`, with replies to the same alias.

1. Resend: add the domain `3senses.design`. Its records sit on `send.3senses.design` and
   `resend._domainkey.3senses.design`, so the alias's own MX and SPF are untouched. Add
   `_dmarc` (`v=DMARC1; p=none; rua=mailto:asksiddha@3senses.design`) if none exists.
2. Secrets, on **both** the service and the `agentic-astrospace-notifications` job:
   `RESEND_API_KEY`, `EMAIL_LINK_SECRET` (any long random string; changing it breaks links
   in emails already sent). On the service only: `RESEND_WEBHOOK_SECRET`.
3. Optional env: `EMAIL_FROM`, `EMAIL_REPLY_TO`, `EMAIL_POSTAL_ADDRESS` (footer sender line), `PUBLIC_BASE_URL`.
4. Resend webhook: `<PUBLIC_BASE_URL>/api/v1/email/webhooks/resend`, events
   `email.bounced` and `email.complained`.
5. Apply `supabase/migrations/20261016120000_add_email_notifications.sql`.
6. Supabase Auth › SMTP: host `smtp.resend.com`, port 465, user `resend`, password the API
   key, sender `asksiddha@3senses.design`. This moves sign-in emails off Supabase's
   rate-limited built-in mailer.

Without `RESEND_API_KEY` or `EMAIL_LINK_SECRET` every email job fails with
"email transport not configured" and stays pending, so adding them later drains the queue.

## Next

Practice reminders, transit alerts and plain-language festival write-ups. The full category map is in
`/mnt/project-files/plans/email_program_setup_2026-10-16.md` in the project's shared files.
Regional festivals wait for the festival-region preference to be stored on the server
(today it is device-only).
