-- Today's Subhashita: a daily verse push, on by default like the morning brief.
--
-- The constraint below is a superset: it also lists the four email categories
-- from 20261016150000_email_batch2.sql (open as PR #144), so applying either
-- migration after the other cannot drop a category the code uses. If #144 is
-- applied after this one, re-run this one.

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
    'tips_email',
    'daily_subhashita'    -- Today's Subhashita, 10:00 local
  ));
