package app.asksiddha.mobile.widgets;

import android.content.Context;
import android.view.View;
import android.widget.RemoteViews;
import app.asksiddha.mobile.R;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Your day: the score ring, the headline and one timing line, on the app's
 * glass card (Liquid Glass at night, Cream Glass by day). Small shows the
 * ring; medium adds the date and headline; large adds the tithi, the summary
 * and one Do and one Avoid as the Today screen's tinted cards.
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
        // The part of the day in force now, on a day the star changes.
        JSONObject now = fresh ? scoreAt(today, System.currentTimeMillis()) : null;
        int score = fresh ? now.optInt("score", 0) : 0;
        String band = fresh ? now.optString("band") : "";
        int arc = bandColor(context, band);
        int ringSize = layout == R.layout.widget_today_small ? 96 : layout == R.layout.widget_today_medium ? 100 : 92;
        views.setImageViewBitmap(R.id.ring,
            Widgets.ring(context, score, arc, Widgets.color(context, R.color.widget_track), ringSize, 8));
        views.setTextViewText(R.id.score, fresh ? String.valueOf(score) : "–");
        // The word under the number says what the score means ("Steady").
        views.setTextViewText(R.id.band, fresh ? now.optString("label") : "");
        views.setTextColor(R.id.band, arc);
        views.setViewVisibility(R.id.band, fresh ? View.VISIBLE : View.GONE);

        String timing = fresh ? TimingWidget.shortLine(today, System.currentTimeMillis()) : "";
        views.setTextViewText(R.id.timing, timing);
        views.setViewVisibility(R.id.timing, timing.isEmpty() ? View.GONE : View.VISIBLE);
        if (layout == R.layout.widget_today_small) return views;

        views.setTextViewText(R.id.headline, fresh
            ? today.optString("headline")
            : "Open Siddha to see your day");
        String date = Widgets.shortDate(WidgetStore.today());

        if (layout == R.layout.widget_today_medium) {
            // "YOUR DAY · WED 21 OCT": the style sets the capitals.
            views.setTextViewText(R.id.eyebrow, "Your day · " + date);
        }

        if (layout == R.layout.widget_today_large) {
            String tithi = fresh ? today.optString("tithi") : "";
            views.setTextViewText(R.id.date_line, tithi.isEmpty() ? date : date + " · " + tithi);
            views.setTextViewText(R.id.summary, fresh ? today.optString("summary") : "");
            String doItem = fresh ? item(today.optString("doItem"), "Do") : "";
            String avoidItem = fresh ? item(today.optString("avoidItem"), "Avoid") : "";
            views.setTextViewText(R.id.do_item, doItem);
            views.setTextViewText(R.id.avoid_item, avoidItem);
            views.setViewVisibility(R.id.do_row, doItem.isEmpty() ? View.GONE : View.VISIBLE);
            views.setViewVisibility(R.id.avoid_row, avoidItem.isEmpty() ? View.GONE : View.VISIBLE);
        }
        return views;
    }

    /**
     * The score, band and label of the part of the day in force at `now`:
     * the last of the day's scoreSteps already begun, else the day's own.
     */
    static JSONObject scoreAt(JSONObject today, long now) {
        JSONArray steps = today.optJSONArray("scoreSteps");
        JSONObject current = today;
        if (steps == null) return current;
        for (int i = 0; i < steps.length(); i++) {
            JSONObject step = steps.optJSONObject(i);
            if (step != null && step.optLong("fromMs") <= now) current = step;
        }
        return current;
    }

    static int bandColor(Context context, String band) {
        return Widgets.color(context, "tough".equals(band) ? R.color.widget_band_tough
            : "mixed".equals(band) ? R.color.widget_band_mixed : R.color.widget_band_steady);
    }

    /**
     * The item without its own label: the row already says Do or Avoid, so
     * "Avoid overextending yourself" reads "Overextending yourself".
     */
    static String item(String text, String label) {
        String t = text == null ? "" : text.trim();
        if (t.regionMatches(true, 0, label + " ", 0, label.length() + 1)) t = t.substring(label.length() + 1).trim();
        if (t.regionMatches(true, 0, label + ":", 0, label.length() + 1)) t = t.substring(label.length() + 1).trim();
        return t.isEmpty() ? t : Character.toUpperCase(t.charAt(0)) + t.substring(1);
    }
}
