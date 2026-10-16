# Email notifications

Status: canonical. How the app emails readers, what it needs in production, and what comes next.

## What is sent

| Email | Category | When (reader's local time) | Source |
| --- | --- | --- | --- |
| Daily reading | `daily_email` | 06:30 (or their `preferred_time`) | the brief the worker already stored for their own profile; skipped if not written by 11:00 |
| Moon and festival days | `festival_email` | 18:00 the evening before | full and new moons (lunar day at sunrise) and pan-India festivals at their place |
| Welcome | `system` | once, when they first turn an email on | what they chose; asks for a birth time when theirs isn't exact |

Both categories are **off by default**. Nothing is emailed until the reader turns one on in
Settings › Notifications › Email (`/api/v1/me/email`). Consent is checked again at send time.

Code: `astrospace/notifications/email.py` (transport, signed links, layout),
`astrospace/notifications/email_jobs.py` (schedulers, delivery),
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

Weekly outlook (needs a weekly agent), monthly outlook, transit alerts, the birth chart
lesson series, compatibility invites and "we miss you". The full category map is in
`/mnt/project-files/plans/email_program_setup_2026-10-16.md` in the project's shared files.
Regional festivals wait for the festival-region preference to be stored on the server
(today it is device-only).
