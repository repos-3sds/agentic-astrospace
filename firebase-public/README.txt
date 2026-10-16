asksiddha.app is a landing page that sends people to Google Play; the app
itself is Android only (Hawk, 2026-10-16). Firebase Hosting serves index.html,
delete-account.html (the Play account-deletion page) and the logo from
this folder, and forwards only /api/** (email unsubscribe),
/legal/** (privacy policy and terms, which the Play listing links to) and
/email/** (the email logo) to the Cloud Run service. Every other path,
including the old web app's /m/..., shows the landing page. See
docs/custom_domain.md.
