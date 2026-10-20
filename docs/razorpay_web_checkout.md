# Razorpay checkout on asksiddha.app

Status: **canonical** — how website purchases work and how to switch them on.

## Why it exists

Google Play keeps 15% of every Play sale. Its Payments policy lets an app
honour a plan bought elsewhere, but the app must never link to or mention the
cheaper route (Play Console Help, "Understanding Google Play's Payments
policy"). So the website sells, the app just sees the plan. Hawk asked for it
on 2026-10-20 after comparing the options (Play-only keeps about ₹255 of
₹300; Razorpay on the web keeps about ₹289).

**Rule for the app:** no link, button or wording that points to buying on the
website. The Plans screen only says a web plan "was not bought in Google
Play, so it is managed where you bought it" and hides the Play manage link.

## How it works

| Piece | Where |
| --- | --- |
| Buy page | `firebase-public/buy.html` + `js/buy.js` → https://asksiddha.app/buy |
| Landing links ("Get Plus on the web") | `firebase-public/js/web-buy.js`; shown only when the server says checkout is open |
| API | `astrospace/api/web_store_routes.py` (`/api/v1/store/web/*`, `/api/v1/store/razorpay/webhook`) |
| Logic | `astrospace/entitlements/razorpay.py` |
| Plans in Razorpay | `scripts/razorpay_setup.py` |
| Refund policy | `astrospace/legal/refunds.html` → /legal/refunds |

1. The reader signs in on /buy with the same Supabase account as the app
   (Google, or an email link for existing accounts only).
2. A plan creates a Razorpay **subscription** (monthly, UPI Autopay or card
   mandate); a question pack creates a Razorpay **order**. Both carry the
   reader's user id in their notes.
3. When checkout closes, `/web/confirm` checks Razorpay's signature, fetches
   the subscription or order back and checks the user id, then writes the
   same `SubscriptionGrant` / `QuestionCredit` rows the Play webhook writes,
   with provider `razorpay`.
4. The webhook keeps it current: renewals, failed renewals (7 days' grace),
   cancellations (access to the end of the paid month), full refunds (plan
   ends or the pack's unused questions go).
5. "Stop renewing" on /buy cancels at the end of the cycle. Deleting the
   account cancels at once.

A plan the reader already pays for (on any store), or a lower one, cannot be
bought again on the web. Moving up from Plus to Practitioner is allowed; a
web Plus then has to be stopped on /buy, and a Play Plus in Google Play.

## Switching it on (Hawk)

1. **Razorpay account.** Sign up at razorpay.com with 3 Senses Design Studio,
   PAN and the bank account. Activation asks for the website: give
   https://asksiddha.app, and point them at /legal/terms, /legal/privacy,
   /legal/refunds and the Contact link. Turn on **Subscriptions**. For buyers
   abroad, also ask for **International payments** (they pay in rupees).
2. **Test first.** In Razorpay's Test mode, copy the test Key ID and secret.
   On the Mac:
   `RAZORPAY_KEY_ID=rzp_test_... RAZORPAY_KEY_SECRET=... python3 scripts/razorpay_setup.py`
   It prints a `RAZORPAY_PLAN_IDS=...` line.
3. **Webhook.** Razorpay › Settings › Webhooks › Add:
   URL `https://asksiddha.app/api/v1/store/razorpay/webhook`, a secret you
   make up, events: `subscription.activated`, `subscription.charged`,
   `subscription.pending`, `subscription.halted`, `subscription.cancelled`,
   `subscription.completed`, `subscription.resumed`, `order.paid`,
   `refund.processed`.
4. **Cloud Run (API service only), keeping every other variable:**
   secrets `RAZORPAY_KEY_SECRET` and `RAZORPAY_WEBHOOK_SECRET` in Secret
   Manager; plain variables `RAZORPAY_KEY_ID`, `RAZORPAY_PLAN_IDS`, and
   `RAZORPAY_ALLOWED_EMAILS=<your email>` so only you can buy while testing.
5. **Supabase › Authentication › URL Configuration:** add
   `https://asksiddha.app/buy` to Redirect URLs.
6. Deploy hosting (`firebase deploy --only hosting`) and the API. Buy Plus on
   /buy with Razorpay's test UPI id `success@razorpay`, check the app shows
   Plus, stop renewing, and buy a question pack.
7. **Go live:** switch to live keys (run the setup script again with them; live
   and test plans are separate), set the live webhook, and remove
   `RAZORPAY_ALLOWED_EMAILS`.

`LEGAL_CONTACT_EMAIL` should be set on the API so the refund page shows the
contact address; Razorpay's review looks for it.

## Not done yet

- GST invoices: Razorpay can email receipts; GST invoicing depends on Hawk's
  registration. Prices are shown as "including any taxes".
- Dollar prices: the web sells in rupees only. Foreign cards work once
  International payments is on.
- iOS: Apple has its own rules for apps that honour web purchases; not checked.
