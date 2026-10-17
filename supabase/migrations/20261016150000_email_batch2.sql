-- Email batch 2: four more email categories, and a record of consent.
--
-- weekly_email    the week ahead, Monday morning
-- monthly_email   the month ahead, on the 1st
-- lessons_email   "Learn your chart", eight short lessons a few days apart
-- tips_email      a note after a long absence, and features worth trying
--
-- New readers who keep the sign-up box ticked get every email category
-- turned on once, at the end of onboarding (POST /api/v1/me/email/defaults);
-- when and where they agreed is kept on their email_recipients row.
-- Readers who signed up before this keep whatever they chose.

alter table public.notification_preferences
  drop constraint if exists notification_preferences_category_check;
alter table public.notification_preferences
  add constraint notification_preferences_category_check check (category in (
    'morning_brief',
    'window_alert',
    'festival_reminder',
    'remedy_reminder',
    'muhurta_reminder',
    'reading_ready',
    'accuracy_review',
    'match_report_ready',
    'system',
    'daily_email',
    'festival_email',
    'weekly_email',
    'monthly_email',
    'lessons_email',
    'tips_email'
  ));

alter table public.email_recipients
  add column if not exists consented_at timestamptz,
  add column if not exists consent_source text;
