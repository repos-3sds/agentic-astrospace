package app.asksiddha.mobile.widgets;

import android.content.Context;
import android.content.Intent;
import android.widget.RemoteViews;
import app.asksiddha.mobile.R;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * The mantra counter: the practice last opened in the app, today's count
 * against its target, and a tap on the ring to count one. Taps are kept here
 * and handed to the app the next time it opens (WidgetsPlugin.takeMantraTaps),
 * so a count made on the home screen is the same count inside the app.
 */
public class MantraWidget extends BaseWidget {

    static final String ACTION_COUNT = "app.asksiddha.mobile.widgets.MANTRA_COUNT";

    @Override
    protected RemoteViews render(Context context, int widthDp, int heightDp) {
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_mantra);
        JSONObject mantra = WidgetStore.get(context, "mantra");
        if (mantra == null) {
            views.setTextViewText(R.id.title, "MANTRA");
            views.setImageViewBitmap(R.id.ring, Widgets.ring(context, 0,
                Widgets.color(context, R.color.widget_accent), Widgets.color(context, R.color.widget_track), 92, 7));
            views.setTextViewText(R.id.count, "ॐ");
            views.setTextViewText(R.id.target, "");
            views.setTextViewText(R.id.hint, "Tap to choose a mantra");
            views.setOnClickPendingIntent(R.id.widget_root, Widgets.open(context, "/m/remedies"));
            return views;
        }
        int target = Math.max(1, mantra.optInt("target", 108));
        int count = todayCount(mantra);
        boolean done = count >= target;
        views.setTextViewText(R.id.title, mantra.optString("title").toUpperCase(java.util.Locale.ROOT));
        views.setImageViewBitmap(R.id.ring, Widgets.ring(context, count * 100 / target,
            Widgets.color(context, done ? R.color.widget_band_steady : R.color.widget_accent),
            Widgets.color(context, R.color.widget_track), 92, 7));
        views.setTextViewText(R.id.count, String.valueOf(count));
        views.setTextViewText(R.id.target, "of " + target);
        views.setTextViewText(R.id.hint, done ? "Completed today" : count == 0 ? "Tap the ring to count" : (target - count) + " to go");
        views.setOnClickPendingIntent(R.id.widget_root, Widgets.open(context, mantra.optString("route", "/m/remedies")));
        if (!done) views.setOnClickPendingIntent(R.id.counter, Widgets.broadcast(context, MantraWidget.class, ACTION_COUNT));
        return views;
    }

    /** A count from an earlier day is not today's: the practice starts again. */
    static int todayCount(JSONObject mantra) {
        return WidgetStore.today().equals(mantra.optString("date")) ? mantra.optInt("count", 0) : 0;
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        if (!ACTION_COUNT.equals(intent.getAction())) {
            super.onReceive(context, intent);
            return;
        }
        JSONObject mantra = WidgetStore.get(context, "mantra");
        if (mantra == null) return;
        int target = Math.max(1, mantra.optInt("target", 108));
        int count = todayCount(mantra);
        if (count >= target) return;
        String today = WidgetStore.today();
        try {
            mantra.put("count", count + 1);
            mantra.put("date", today);
        } catch (JSONException e) {
            return;
        }
        WidgetStore.put(context, "mantra", mantra.toString());
        WidgetStore.addMantraTap(context, mantra.optString("key"), today);
        Widgets.refresh(context, MantraWidget.class);
    }
}
