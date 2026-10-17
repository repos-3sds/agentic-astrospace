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
        views.setImageViewBitmap(R.id.moon, Widgets.moon(context, System.currentTimeMillis(), 56));

        JSONObject today = WidgetStore.get(context, "today");
        boolean fresh = today != null && WidgetStore.today().equals(today.optString("date"));
        views.setTextViewText(R.id.tithi, fresh ? today.optString("tithi") : "The moon today");
        views.setTextViewText(R.id.next, nextMoon(WidgetStore.get(context, "calendar")));
        return views;
    }

    static String nextMoon(JSONObject calendar) {
        if (calendar == null) return "";
        JSONArray moons = calendar.optJSONArray("moonDays");
        String today = WidgetStore.today();
        JSONObject next = CalendarWidget.firstFrom(moons, today);
        if (next == null) return "";
        boolean full = "full".equals(next.optString("moon"));
        String when = Widgets.daysUntil(today, next.optString("date"));
        if ("today".equals(when)) return full ? "Purnima today" : "Amavasya today";
        return (full ? "Purnima " : "Amavasya ") + when;
    }
}
