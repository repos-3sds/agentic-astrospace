package app.asksiddha.mobile.widgets;

import android.content.Context;
import android.widget.RemoteViews;
import app.asksiddha.mobile.R;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * One timing window, counting (Figma M10 Live Activity, node 106:92, as a
 * home-screen widget). The window is the one the app's timing note names
 * (Rahu Kalam) while it is ahead or running; after it, the next window of
 * the day. The countdown is in minutes ("Starts in 6h 57m"): a per-minute
 * tick (Widgets.scheduleTick) redraws it while a window is still ahead.
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

        int track = Widgets.color(context, R.color.widget_track);
        if (window == null) {
            views.setImageViewBitmap(R.id.dot, Widgets.ring(context, 0, track, track, 44, 5));
            views.setTextViewText(R.id.name, fresh ? "TODAY’S WINDOWS" : "TIMING");
            views.setTextViewText(R.id.status, fresh ? "All done for today" : "Open Siddha for today");
            views.setTextViewText(R.id.span, fresh ? "Tomorrow’s appear at midnight" : "");
            return views;
        }

        long start = window.optLong("startMs"), end = window.optLong("endMs");
        boolean running = now >= start;
        boolean caution = "inauspicious".equals(window.optString("kind"));
        int tone = Widgets.color(context, caution ? R.color.widget_accent : R.color.widget_band_steady);
        views.setImageViewBitmap(R.id.dot, Widgets.ring(context, fill(start, end, now), tone, track, 44, 5));
        views.setTextViewText(R.id.name, window.optString("name").toUpperCase(java.util.Locale.ROOT));
        views.setTextViewText(R.id.status, running
            ? "Ends in " + Widgets.duration(end - now)
            : "Starts in " + Widgets.duration(start - now));
        views.setTextViewText(R.id.span, Widgets.clock(start) + " – " + Widgets.clock(end));
        return views;
    }

    /** How long before a window the ring starts filling. */
    static final long LEAD_MS = 3 * 3600_000L;

    /**
     * The ring fills over the three hours before a window and is full as it
     * starts; while it runs it empties, like the Live Activity's.
     */
    static int fill(long start, long end, long now) {
        if (now >= start) return end > start ? (int) (100 * (end - now) / (end - start)) : 0;
        long ahead = start - now;
        return ahead >= LEAD_MS ? 4 : (int) (100 - 96 * ahead / LEAD_MS);
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
