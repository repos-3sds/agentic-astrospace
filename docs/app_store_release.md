# Releasing Siddha on the App Store

Status: canonical. What stands between a TestFlight build and an App Store
release, what the code already does for App Review, and the steps only the
account holder can take. TestFlight itself: [ship_ios_testflight.md](ship_ios_testflight.md).

Apple has no tester-count or 14-day rule. A build can be submitted for review
whenever the steps below are done; review usually takes 1 to 2 days, and the
listing is set to manual release, so nothing goes live until Hawk presses
Release. Nothing in CI submits for review (`scripts/asc.py` has no review call).

## What the app already does for App Review

| Guideline | Where |
| --- | --- |
| 3.1.1 purchases go through the App Store | `core/purchase.service.ts` (RevenueCat, `appl_` key in `environment.prod.ts`) |
| 3.1.1 Restore purchases | Plans footer |
| 3.1.2 subscription terms beside the buy button, Terms of Use (EULA) and Privacy Policy links | Plans, `renewalTerms()` and footer |
| 2.3.10 no other store named on iPhone | Plans names only the App Store (`storeName`) |
| 3.1.3 no pointer to buying on the website | Plans says only that a web plan "is managed where you bought it" |
| 5.1.1(v) account deletion in the app | Settings › Account & privacy › Delete account |
| 5.1.2(i) consent before data goes to a third-party AI | Setup screen "Written with AI"; once in Ask for readers who skipped it (`ai-sharing-sheet.component.ts`) |
| 1.2 / AI content: report an answer | "Report this answer" under each Ask answer |
| 4.8 Sign in with Apple | Native Apple sheet on the sign-in screen |
| 2.1 demo account | `smartagenticais+review@gmail.com` with a password (already in App Review Information) |

Reviewers buy in Apple's sandbox. The webhook applies sandbox purchases for
the accounts in `REVENUECAT_SANDBOX_EMAILS` (default: the review account), so
their purchase unlocks the plan even after `REVENUECAT_ACCEPT_SANDBOX` is
turned off for launch (`astrospace/api/store_routes.py`).

## Steps only Hawk can take

In order. The browser thread can do the App Store Connect and RevenueCat
screens with Hawk's yes typed there, except the agreement, bank and tax pages.

1. **Paid Apps agreement.** App Store Connect › Business › Agreements: accept
   the Paid Apps agreement (Account Holder only).
2. **Bank account and tax forms.** Same page: add the bank account that
   receives payouts, and complete the tax forms (the US form is the W-8BEN for
   an individual outside the US; India's tax info too). The agreement shows
   *Active* only when both are done, and products can't be bought before that.
3. **Create the products.** App Store Connect › the app › Monetization:
   - Subscriptions: group `Siddha plans`; `siddha_plus_monthly` (1 month,
     India ₹300, United States $9.99) and `siddha_practitioner_monthly`
     (1 month, ₹1,000 / $24.99), Practitioner ranked above Plus in the group.
   - In-App Purchases, Consumable: `siddha_questions_1` (₹50 / $2.99) and
     `siddha_questions_3` (₹130 / $6.99).
   - Each needs a display name, description and a review screenshot (the Plans
     screen). Let Apple derive other countries from the US price.
   The IDs must match exactly: the server maps purchases by these IDs
   (`astrospace/entitlements/products.py`).
4. **RevenueCat.** Project › Apps › add an App Store app for
   `app.asksiddha.mobile`; upload the In-App Purchase key (App Store Connect ›
   Users and Access › Integrations › In-App Purchase, a `.p8`) and the App
   Store Connect API key. Import the four products, attach the two plans to
   the `plus` and `pro` entitlements, and add them to the default offering.
   Point App Store Server Notifications (App Store Connect › App Information)
   at RevenueCat's URL shown there.
5. **The `appl_` key.** RevenueCat › Project › API keys › the App Store public
   key. It is public by design; a one-line PR puts it in
   `ui/src/environments/environment.prod.ts` (`revenueCat.ios`), and the merge
   ships a TestFlight build with purchases on.
6. **Test in TestFlight.** Buy Plus and a question pack with a sandbox
   tester (App Store Connect › Users and Access › Sandbox), then Restore.
7. **App Store listing.** Add to the description:
   `Terms of Use: https://asksiddha.app/legal/terms` (or set the EULA field in
   App Information), and attach the subscriptions to the version under
   *In-App Purchases and Subscriptions*.
8. **Submit for review**, on Hawk's word only.

Before launch: turn `REVENUECAT_ACCEPT_SANDBOX` and
`ASTROSPACE_TESTERS_GET_PLUS` off on the API; leave `REVENUECAT_SANDBOX_EMAILS`
unset so the review account keeps working for every later review.
