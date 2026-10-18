package app.asksiddha.mobile.widgets;

import android.content.Context;
import android.widget.RemoteViews;
import app.asksiddha.mobile.R;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Calendar, the app's main tab on the home screen. Medium: today's date,
 * tithi and nakshatra, and the next festival or moon day. Large: the month,
 * festival days marked, as the Calendar tab draws it.
 */
public class CalendarWidget extends BaseWidget {

    @Override
    protected RemoteViews render(Context context, int widthDp, int heightDp) {
        boolean month = heightDp >= 220;
        RemoteViews views = new RemoteViews(context.getPackageName(),
            month ? R.layout.widget_calendar_month : R.layout.widget_calendar);
        views.setOnClickPendingIntent(R.id.widget_root, Widgets.open(context, "/m/calendar"));

        JSONObject today = WidgetStore.get(context, "today");
        boolean fresh = today != null && WidgetStore.today().equals(today.optString("date"));
        JSONObject calendar = WidgetStore.get(context, "calendar");
        Date now = new Date();

        if (month) {
            views.setTextViewText(R.id.month, new SimpleDateFormat("MMMM yyyy", Locale.ENGLISH).format(now));
            views.setTextViewText(R.id.tithi, fresh ? today.optString("tithi") : "");
            drawMonth(context, views, calendar);
        } else {
            views.setTextViewText(R.id.weekday, new SimpleDateFormat("EEE", Locale.ENGLISH).format(now).toUpperCase(Locale.ROOT));
            views.setTextViewText(R.id.day, new SimpleDateFormat("d", Locale.ENGLISH).format(now));
            views.setTextViewText(R.id.month, new SimpleDateFormat("MMMM", Locale.ENGLISH).format(now));
            views.setTextViewText(R.id.tithi, fresh ? today.optString("tithi") : "Open Siddha for today");
            views.setTextViewText(R.id.nakshatra, fresh ? today.optString("nakshatra") + " nakshatra" : "");
        }
        views.setTextViewText(R.id.next, nextLine(calendar));
        return views;
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

    private static void drawMonth(Context context, RemoteViews views, JSONObject calendar) {
        Set<String> marked = new HashSet<>();
        if (calendar != null) {
            JSONArray festivals = calendar.optJSONArray("festivals");
            for (int i = 0; festivals != null && i < festivals.length(); i++) {
                JSONObject f = festivals.optJSONObject(i);
                if (f != null) marked.add(f.optString("date"));
            }
        }
        String pkg = context.getPackageName();
        views.removeAllViews(R.id.grid);

        RemoteViews head = new RemoteViews(pkg, R.layout.widget_calendar_row);
        for (String d : new String[] {"S", "M", "T", "W", "T", "F", "S"}) {
            RemoteViews cell = new RemoteViews(pkg, R.layout.widget_calendar_cell_head);
            cell.setTextViewText(R.id.cell, d);
            head.addView(R.id.row, cell);
        }
        views.addView(R.id.grid, head);

        Calendar c = Calendar.getInstance();
        int today = c.get(Calendar.DAY_OF_MONTH);
        int days = c.getActualMaximum(Calendar.DAY_OF_MONTH);
        c.set(Calendar.DAY_OF_MONTH, 1);
        int lead = c.get(Calendar.DAY_OF_WEEK) - Calendar.SUNDAY;
        String prefix = new SimpleDateFormat("yyyy-MM-", Locale.US).format(c.getTime());

        int day = 1 - lead;
        while (day <= days) {
            RemoteViews row = new RemoteViews(pkg, R.layout.widget_calendar_row);
            for (int col = 0; col < 7; col++, day++) {
                String iso = prefix + (day < 10 ? "0" + day : String.valueOf(day));
                int layout = day == today ? R.layout.widget_calendar_cell_today
                    : day >= 1 && day <= days && marked.contains(iso) ? R.layout.widget_calendar_cell_event
                    : R.layout.widget_calendar_cell_plain;
                RemoteViews cell = new RemoteViews(pkg, layout);
                cell.setTextViewText(R.id.cell, day >= 1 && day <= days ? String.valueOf(day) : "");
                row.addView(R.id.row, cell);
            }
            views.addView(R.id.grid, row);
        }
    }
}
