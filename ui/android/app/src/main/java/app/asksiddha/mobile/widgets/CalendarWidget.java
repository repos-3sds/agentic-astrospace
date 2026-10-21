package app.asksiddha.mobile.widgets;

import android.content.Context;
import android.text.SpannableStringBuilder;
import android.text.Spanned;
import android.text.style.ForegroundColorSpan;
import android.view.View;
import android.widget.RemoteViews;
import app.asksiddha.mobile.R;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Calendar, the app's main tab on the home screen. By default the next seven
 * days from today, each tinted as the Calendar tab tints it (good day for you,
 * take care) with a dot for a festival or vrat, and the week's festivals
 * listed under it; taller shows more of them. Made small (2x2) it shows today
 * alone. Hawk (2026-10-21) found a month grid not useful as a widget.
 */
public class CalendarWidget extends BaseWidget {

    /** A day of the week strip and its "coming up" row, by date. */
    private static final class Event {
        final String date;
        final CharSequence text;

        Event(String date, CharSequence text) {
            this.date = date;
            this.text = text;
        }
    }

    @Override
    protected RemoteViews render(Context context, int widthDp, int heightDp) {
        JSONObject today = WidgetStore.get(context, "today");
        boolean fresh = today != null && WidgetStore.today().equals(today.optString("date"));
        JSONObject calendar = WidgetStore.get(context, "calendar");

        RemoteViews views;
        if (widthDp > 0 && widthDp < 200) {
            views = new RemoteViews(context.getPackageName(), R.layout.widget_calendar_small);
            drawDay(context, views, fresh ? today : null, calendar, false);
        } else {
            views = new RemoteViews(context.getPackageName(), R.layout.widget_calendar_week);
            drawWeek(context, views, fresh ? today : null, calendar, heightDp);
        }
        views.setOnClickPendingIntent(R.id.widget_root, Widgets.open(context, "/m/calendar"));
        return views;
    }

    /** Today on its own: the 2x2 widget, and the 4x2 day layout when `full`. */
    static void drawDay(Context context, RemoteViews views, JSONObject today, JSONObject calendar, boolean full) {
        Date now = new Date();
        String iso = WidgetStore.today();
        JSONObject day = dayRow(calendar, iso);
        String weekday = new SimpleDateFormat("EEE", Locale.ENGLISH).format(now);
        String month = new SimpleDateFormat("MMMM", Locale.ENGLISH).format(now);
        views.setTextViewText(R.id.weekday, full ? weekday : weekday + " · " + month);
        views.setTextViewText(R.id.day, new SimpleDateFormat("d", Locale.ENGLISH).format(now));
        String tithi = today != null ? today.optString("tithi") : day != null ? day.optString("tithi") : "";
        views.setTextViewText(R.id.tithi, tithi.isEmpty() ? "Open Siddha for today" : tithi);
        quality(context, views, day == null ? "" : day.optString("quality"));
        if (full) {
            views.setTextViewText(R.id.month, month);
            views.setTextViewText(R.id.nakshatra, today != null ? today.optString("nakshatra") + " nakshatra" : "");
            views.setTextViewText(R.id.next, nextLine(calendar));
        }
    }

    /** "Good day for you" or "Take care today" as a tinted chip; nothing on a mixed day. */
    private static void quality(Context context, RemoteViews views, String quality) {
        boolean good = "good".equals(quality), care = "care".equals(quality);
        views.setViewVisibility(R.id.quality, good || care ? View.VISIBLE : View.GONE);
        if (!good && !care) return;
        views.setTextViewText(R.id.quality, good ? "Good day for you" : "Take care today");
        views.setTextColor(R.id.quality, Widgets.color(context, good ? R.color.widget_good : R.color.widget_warn));
        views.setInt(R.id.quality, "setBackgroundResource", good ? R.drawable.widget_chip_good : R.drawable.widget_chip_care);
    }

    private static void drawWeek(Context context, RemoteViews views, JSONObject today, JSONObject calendar, int heightDp) {
        String pkg = context.getPackageName();
        List<String> dates = weekFrom(WidgetStore.today());
        JSONObject first = dayRow(calendar, dates.get(0));
        String tithi = today != null ? today.optString("tithi") : first != null ? first.optString("tithi") : "";
        views.setTextViewText(R.id.tithi, tithi.isEmpty() ? "" : "Today: " + tithi);

        List<Event> events = weekEvents(context, calendar, dates);
        Set<String> marked = new HashSet<>();
        for (Event e : events) marked.add(e.date);

        views.removeAllViews(R.id.week);
        SimpleDateFormat in = new SimpleDateFormat("yyyy-MM-dd", Locale.US);
        for (int i = 0; i < dates.size(); i++) {
            String iso = dates.get(i);
            JSONObject row = dayRow(calendar, iso);
            String q = row == null ? "" : row.optString("quality");
            boolean good = "good".equals(q), care = "care".equals(q), isToday = i == 0;
            RemoteViews cell = new RemoteViews(pkg, R.layout.widget_calendar_week_day);
            Date date = parse(in, iso);
            String weekday = new SimpleDateFormat("EEE", Locale.ENGLISH).format(date);
            cell.setTextViewText(R.id.weekday, isToday ? "Today" : weekday);
            cell.setTextColor(R.id.weekday, Widgets.color(context, isToday ? R.color.widget_text : R.color.widget_muted));
            cell.setTextViewText(R.id.date, iso.substring(8).replaceFirst("^0", ""));
            cell.setTextColor(R.id.date, Widgets.color(context,
                good ? R.color.widget_good : care ? R.color.widget_warn : R.color.widget_text));
            int background = isToday
                ? (good ? R.drawable.widget_day_today_good : care ? R.drawable.widget_day_today_care : R.drawable.widget_day_today)
                : good ? R.drawable.widget_day_good : care ? R.drawable.widget_day_care : 0;
            cell.setInt(R.id.date, "setBackgroundResource", background);
            cell.setViewVisibility(R.id.dot, marked.contains(iso) ? View.VISIBLE : View.INVISIBLE);
            // A tint or a dot means nothing to TalkBack; say it.
            cell.setContentDescription(R.id.date, new SimpleDateFormat("EEEE d MMMM", Locale.ENGLISH).format(date)
                + (isToday ? ", today" : "") + (good ? ", a good day for you" : care ? ", a day to take care" : "")
                + (marked.contains(iso) ? ", festival or vrat" : ""));
            views.addView(R.id.week, Widgets.capText(context, cell));
        }

        // 4x2 has room for one row (none on a launcher whose two rows are
        // short); 4x3 for three; 4x4 and up for five.
        int rows = heightDp > 0 && heightDp < 150 ? 0 : heightDp < 200 ? 1 : heightDp < 280 ? 3 : 5;
        views.removeAllViews(R.id.events);
        views.setViewVisibility(R.id.events, rows == 0 ? View.GONE : View.VISIBLE);
        if (events.isEmpty() && rows > 0) {
            String next = nextLine(calendar);
            RemoteViews row = new RemoteViews(pkg, R.layout.widget_calendar_event);
            row.setTextViewText(R.id.when, next.isEmpty() ? "" : "Next");
            row.setTextViewText(R.id.what, next.isEmpty() ? "No festivals this week" : next);
            views.addView(R.id.events, Widgets.capText(context, row));
        }
        for (int i = 0; i < events.size() && i < rows; i++) {
            Event e = events.get(i);
            RemoteViews row = new RemoteViews(pkg, R.layout.widget_calendar_event);
            row.setTextViewText(R.id.when, e.date.equals(dates.get(0)) ? "Today"
                : new SimpleDateFormat("EEE d", Locale.ENGLISH).format(parse(in, e.date)));
            row.setTextViewText(R.id.what, e.text);
            views.addView(R.id.events, Widgets.capText(context, row));
        }
        views.setViewVisibility(R.id.legend, heightDp >= 240 ? View.VISIBLE : View.GONE);
    }

    /** Today and the six days after it, as YYYY-MM-DD. */
    static List<String> weekFrom(String todayIso) {
        List<String> dates = new ArrayList<>();
        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd", Locale.US);
        Calendar c = Calendar.getInstance();
        c.setTime(parse(f, todayIso));
        for (int i = 0; i < 7; i++) {
            dates.add(f.format(c.getTime()));
            c.add(Calendar.DAY_OF_MONTH, 1);
        }
        return dates;
    }

    /**
     * The week's festivals, vrat days and full and new moons, one row a day
     * in date order. A vrat a festival already names (Kartika Purnima) and a
     * moon a vrat already names (Purnima, Amavasya) are not listed twice.
     */
    static List<Event> weekEvents(Context context, JSONObject calendar, List<String> dates) {
        List<Event> out = new ArrayList<>();
        if (calendar == null) return out;
        String from = dates.get(0), to = dates.get(dates.size() - 1);
        Map<String, SpannableStringBuilder> byDate = new HashMap<>();
        Map<String, String> names = new HashMap<>();
        int muted = Widgets.color(context, R.color.widget_muted);
        for (String key : new String[] {"festivals", "vrats"}) {
            JSONArray rows = calendar.optJSONArray(key);
            for (int i = 0; rows != null && i < rows.length(); i++) {
                JSONObject row = rows.optJSONObject(i);
                if (row == null) continue;
                String date = row.optString("date"), name = row.optString("name");
                if (date.compareTo(from) < 0 || date.compareTo(to) > 0 || name.isEmpty()) continue;
                String seen = names.containsKey(date) ? names.get(date) : "";
                if (covered(seen, name)) continue;
                SpannableStringBuilder text = byDate.get(date);
                if (text == null) {
                    text = new SpannableStringBuilder();
                    byDate.put(date, text);
                } else {
                    text.append(", ");
                }
                text.append(name);
                names.put(date, seen + " " + name.toLowerCase(Locale.ROOT));
                if (row.optBoolean("approx", false) && !text.toString().contains("varies by tradition")) {
                    int start = text.length();
                    text.append(" · varies by tradition");
                    text.setSpan(new ForegroundColorSpan(muted), start, text.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
                }
            }
        }
        JSONArray moons = calendar.optJSONArray("moonDays");
        for (int i = 0; moons != null && i < moons.length(); i++) {
            JSONObject row = moons.optJSONObject(i);
            if (row == null) continue;
            String date = row.optString("date");
            if (date.compareTo(from) < 0 || date.compareTo(to) > 0) continue;
            boolean full = "full".equals(row.optString("moon"));
            String seen = names.containsKey(date) ? names.get(date) : "";
            if (seen.contains(full ? "purnima" : "amavasya") || seen.contains(full ? "full moon" : "new moon")) continue;
            SpannableStringBuilder text = byDate.get(date);
            if (text == null) {
                byDate.put(date, new SpannableStringBuilder(full ? "Full moon" : "New moon"));
            } else {
                text.append(full ? " · full moon" : " · new moon");
            }
        }
        for (String date : dates) {
            if (byDate.containsKey(date)) out.add(new Event(date, byDate.get(date)));
        }
        return out;
    }

    /** A vrat a festival on the same day already covers (Vaikuntha Ekadashi). */
    private static boolean covered(String seen, String name) {
        String n = name.toLowerCase(Locale.ROOT);
        for (String word : new String[] {"ekadashi", "pradosh", "purnima", "amavasya"}) {
            if (n.contains(word) && seen.contains(word)) return true;
        }
        return false;
    }

    /** The app's row for a date in the calendar part's `days`, if it sent one. */
    static JSONObject dayRow(JSONObject calendar, String iso) {
        JSONArray days = calendar == null ? null : calendar.optJSONArray("days");
        for (int i = 0; days != null && i < days.length(); i++) {
            JSONObject row = days.optJSONObject(i);
            if (row != null && iso.equals(row.optString("date"))) return row;
        }
        return null;
    }

    private static Date parse(SimpleDateFormat f, String iso) {
        try {
            return f.parse(iso);
        } catch (java.text.ParseException e) {
            return new Date();
        }
    }

    /** "Diwali · in 3 days", or the next full or new moon when it comes first. */
    static String nextLine(JSONObject calendar) {
        if (calendar == null) return "";
        String today = WidgetStore.today();
        JSONObject festival = firstFrom(calendar.optJSONArray("festivals"), today);
        JSONObject moon = firstFrom(calendar.optJSONArray("moonDays"), today);
        if (festival == null && moon == null) return "";
        boolean moonFirst = festival == null
            || (moon != null && moon.optString("date").compareTo(festival.optString("date")) < 0);
        if (moonFirst) {
            String name = "full".equals(moon.optString("moon")) ? "Full moon" : "New moon";
            return name + " · " + Widgets.daysUntil(today, moon.optString("date"))
                + (moon.optBoolean("approx", true) ? " · by sunrise" : "");
        }
        return festival.optString("name") + " · " + Widgets.daysUntil(today, festival.optString("date"))
            + (festival.optBoolean("approx", false) ? " · varies by tradition" : "");
    }

    static JSONObject firstFrom(JSONArray rows, String fromIso) {
        if (rows == null) return null;
        JSONObject best = null;
        for (int i = 0; i < rows.length(); i++) {
            JSONObject row = rows.optJSONObject(i);
            if (row == null || row.optString("date").compareTo(fromIso) < 0) continue;
            if (best == null || row.optString("date").compareTo(best.optString("date")) < 0) best = row;
        }
        return best;
    }
}
