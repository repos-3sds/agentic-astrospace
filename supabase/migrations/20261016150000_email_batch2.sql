-- Email batch 2: four more email categories, and a record of consent.
--
-- weekly_email    the week ahead, Monday morning
-- monthly_email   the month ahead, on the 1st
-- lessons_email   "Learn your chart", eight short lessons a few days apart
-- tips_email      a note after a long absence, and features worth trying
--
-- The four categories are already allowed: 20261017120000_add_daily_subhashita
-- redefined notification_preferences_category_check with them (and
-- daily_subhashita), so this file must not redefine that check again.
--
-- New readers who keep the sign-up box ticked get every email category
-- turned on once, at the end of onboarding (POST /api/v1/me/email/defaults);
-- when and where they agreed is kept on their email_recipients row.
-- Readers who signed up before this keep whatever they chose.

alter table public.email_recipients
  add column if not exists consented_at timestamptz,
  add column if not exists consent_source text;
