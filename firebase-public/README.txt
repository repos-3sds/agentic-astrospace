asksiddha.app is a landing page that sends people to Google Play; the app
itself is Android only (Hawk, 2026-10-16). Firebase Hosting serves index.html,
delete-account.html (the Play account-deletion page), img/ (galaxy icon,
share image, app screenshots), fonts/ (the Samarkan wordmark) and the
old logo from this folder, and forwards only /api/** (email unsubscribe),
/legal/** (privacy policy and terms, which the Play listing links to) and
/email/** (the email logo) to the Cloud Run service. Every other path,
including the old web app's /m/..., shows the landing page. See
docs/custom_domain.md.

The screenshots in img/screens/ are real captures of the app's /m screens
(main 6110097, 2026-10-20) with a made-up sample profile, one per theme,
with a phone status bar added on top. The page picks the light or dark one
from the visitor's system theme and draws a Galaxy S25 Ultra frame around
them in CSS. Retake them when the screens change rather than editing them.
