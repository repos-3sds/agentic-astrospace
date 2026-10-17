package app.asksiddha.mobile.widgets;

import android.content.Context;
import android.view.View;
import android.widget.RemoteViews;
import app.asksiddha.mobile.R;
import org.json.JSONObject;

/**
 * Your day: the score ring, the headline and one timing line (Figma M10
 * Home Screen Widget, node 103:92). Small shows the ring; medium adds the
 * headline; large adds the summary and one Do and one Avoid.
 */
public class TodayWidget extends BaseWidget {

    @Override
    protected RemoteViews render(Context context, int widthDp, int heightDp) {
        int layout = widthDp < 200 ? R.layout.widget_today_small
            : heightDp >= 220 ? R.layout.widget_today_large
            : R.layout.widget_today_medium;
        RemoteViews views = new RemoteViews(context.getPackageName(), layout);
        views.setOnClickPendingIntent(R.id.widget_root, Widgets.open(context, "/m/today"));

        JSONObject today = WidgetStore.get(context, "today");
        boolean fresh = today != null && WidgetStore.today().equals(today.optString("date"));
        int score = fresh ? today.optInt("score", 0) : 0;
        String band = fresh ? today.optString("band") : "";
        int arc = Widgets.color(context, "tough".equals(band) ? R.color.widget_accent
            : "mixed".equals(band) ? R.color.widget_warn : R.color.widget_good);
        int ringSize = layout == R.layout.widget_today_medium ? 84 : 76;
        views.setImageViewBitmap(R.id.ring,
            Widgets.ring(context, score, arc, Widgets.color(context, R.color.widget_track), ringSize, 9));
        views.setTextViewText(R.id.score, fresh ? String.valueOf(score) : "–");

        if (layout == R.layout.widget_today_small) {
            views.setTextViewText(R.id.label, fresh ? today.optString("label") : "Open Siddha");
            String timing = fresh ? TimingWidget.shortLine(today, System.currentTimeMillis()) : "";
            views.setTextViewText(R.id.timing, timing);
            views.setViewVisibility(R.id.timing, timing.isEmpty() ? View.GONE : View.VISIBLE);
            return views;
        }

        views.setTextViewText(R.id.headline, fresh
            ? today.optString("headline")
            : "Open Siddha to see your day");
        String timing = fresh ? TimingWidget.shortLine(today, System.currentTimeMillis()) : "";
        views.setTextViewText(R.id.timing, timing);
        views.setViewVisibility(R.id.timing, timing.isEmpty() ? View.GONE : View.VISIBLE);

        if (layout == R.layout.widget_today_large) {
            views.setTextViewText(R.id.summary, fresh ? today.optString("summary") : "");
            String doItem = fresh ? today.optString("doItem") : "";
            String avoidItem = fresh ? today.optString("avoidItem") : "";
            views.setTextViewText(R.id.do_item, doItem.isEmpty() ? "" : "Do · " + doItem);
            views.setTextViewText(R.id.avoid_item, avoidItem.isEmpty() ? "" : "Avoid · " + avoidItem);
            views.setViewVisibility(R.id.do_item, doItem.isEmpty() ? View.GONE : View.VISIBLE);
            views.setViewVisibility(R.id.avoid_item, avoidItem.isEmpty() ? View.GONE : View.VISIBLE);
        }
        return views;
    }
}
