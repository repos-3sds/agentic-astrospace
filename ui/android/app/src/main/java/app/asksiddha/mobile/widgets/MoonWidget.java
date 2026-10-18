package app.asksiddha.mobile.widgets;

import android.content.Context;
import android.widget.RemoteViews;
import app.asksiddha.mobile.R;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * The moon today: its shape, the tithi, and the next full or new moon day.
 * The dates are the app's (tithi at sunrise at the reader's place, the rule
 * the server states with them); only the drawing is approximate.
 */
public class MoonWidget extends BaseWidget {

    @Override
    protected RemoteViews render(Context context, int widthDp, int heightDp) {
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_moon);
        views.setOnClickPendingIntent(R.id.widget_root, Widgets.open(context, "/m/calendar"));
        views.setImageViewBitmap(R.id.moon, Widgets.moon(context, System.currentTimeMillis(), 72));

        JSONObject today = WidgetStore.get(context, "today");
        boolean fresh = today != null && WidgetStore.today().equals(today.optString("date"));
        views.setTextViewText(R.id.tithi, fresh ? today.optString("tithi") : "The moon today");
        JSONObject next = nextMoon(WidgetStore.get(context, "calendar"));
        if (next == null) {
            views.setTextViewText(R.id.next_name, "");
            views.setTextViewText(R.id.next, "");
            return views;
        }
        boolean full = "full".equals(next.optString("moon"));
        String date = next.optString("date");
        String when = Widgets.daysUntil(WidgetStore.today(), date);
        views.setTextViewText(R.id.next_name, full ? "PURNIMA" : "AMAVASYA");
        // The day is the one whose sunrise falls in the 15th tithi; some
        // calendars use the day the tithi begins, so the rule rides along.
        String rule = next.optBoolean("approx", true) ? " · by sunrise" : "";
        views.setTextViewText(R.id.next, ("today".equals(when) ? "Today"
            : Widgets.shortDate(date) + " · " + when) + rule);
        return views;
    }

    /** The next full or new moon day from today, as the app's panchanga dates it. */
    static JSONObject nextMoon(JSONObject calendar) {
        if (calendar == null) return null;
        JSONArray moons = calendar.optJSONArray("moonDays");
        return CalendarWidget.firstFrom(moons, WidgetStore.today());
    }
}
