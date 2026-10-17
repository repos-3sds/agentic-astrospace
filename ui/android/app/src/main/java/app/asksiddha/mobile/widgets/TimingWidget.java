package app.asksiddha.mobile.widgets;

import android.content.Context;
import android.os.SystemClock;
import android.view.View;
import android.widget.RemoteViews;
import app.asksiddha.mobile.R;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * One timing window, counting (Figma M10 Live Activity, node 106:92, as a
 * home-screen widget). The window is the one the app's timing note names
 * (Rahu Kalam) while it is ahead or running; after it, the next window of
 * the day. The countdown is a Chronometer, so it ticks without waking the app.
 */
public class TimingWidget extends BaseWidget {

    @Override
    protected RemoteViews render(Context context, int widthDp, int heightDp) {
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_timing);
        views.setOnClickPendingIntent(R.id.widget_root, Widgets.open(context, "/m/calendar"));

        long now = System.currentTimeMillis();
        JSONObject today = WidgetStore.get(context, "today");
        boolean fresh = today != null && WidgetStore.today().equals(today.optString("date"));
        JSONObject window = fresh ? current(today, now) : null;

        if (window == null) {
            views.setImageViewBitmap(R.id.dot, Widgets.ring(context, 100,
                Widgets.color(context, R.color.widget_track), Widgets.color(context, R.color.widget_track), 36, 5));
            views.setTextViewText(R.id.name, fresh ? "TODAY’S WINDOWS" : "TIMING");
            views.setTextViewText(R.id.status, fresh ? "All done for today" : "Open Siddha for today");
            views.setViewVisibility(R.id.clock, View.GONE);
            views.setViewVisibility(R.id.status, View.VISIBLE);
            return views;
        }

        long start = window.optLong("startMs"), end = window.optLong("endMs");
        boolean running = now >= start;
        boolean caution = "inauspicious".equals(window.optString("kind"));
        int tone = Widgets.color(context, caution ? R.color.widget_accent : R.color.widget_good);
        // The ring empties as a running window runs out, like the Live Activity's.
        int left = running && end > start ? (int) (100 * (end - now) / (end - start)) : 100;
        views.setImageViewBitmap(R.id.dot,
            Widgets.ring(context, left, tone, Widgets.color(context, R.color.widget_track), 36, 5));
        views.setTextViewText(R.id.name, window.optString("name").toUpperCase(java.util.Locale.ROOT));

        long target = running ? end : start;
        // Chronometer counts against the elapsed-realtime clock, not the wall clock.
        long base = SystemClock.elapsedRealtime() + (target - now);
        views.setChronometer(R.id.clock, base, running ? "Ends in %s" : "Starts in %s", true);
        views.setChronometerCountDown(R.id.clock, true);
        views.setViewVisibility(R.id.clock, View.VISIBLE);
        views.setViewVisibility(R.id.status, View.GONE);
        return views;
    }

    /** The window to show: Rahu Kalam until it ends, then the next one ahead. */
    static JSONObject current(JSONObject today, long now) {
        JSONArray windows = today.optJSONArray("windows");
        if (windows == null) return null;
        JSONObject best = null;
        for (int i = 0; i < windows.length(); i++) {
            JSONObject w = windows.optJSONObject(i);
            if (w == null || w.optLong("endMs") <= now) continue;
            if (w.optString("name").startsWith("Rahu Kalam")) return w;
            if (best == null || w.optLong("startMs") < best.optLong("startMs")) best = w;
        }
        return best;
    }

    /** "Rahu Kalam in 2h" or "Rahu Kalam ends in 38 min", for the Today widget. */
    static String shortLine(JSONObject today, long now) {
        JSONObject w = current(today, now);
        if (w == null) return "";
        long start = w.optLong("startMs"), end = w.optLong("endMs");
        String name = w.optString("name");
        return now < start
            ? name + " in " + Widgets.duration(start - now)
            : name + " ends in " + Widgets.duration(end - now);
    }
}
