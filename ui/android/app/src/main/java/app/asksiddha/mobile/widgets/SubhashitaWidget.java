package app.asksiddha.mobile.widgets;

import android.content.Context;
import android.view.View;
import android.widget.RemoteViews;
import app.asksiddha.mobile.R;
import org.json.JSONObject;

/**
 * Today's Subhashita, drawn as the app's Subhashita card: the same
 * red-to-dark ground, centred column and gold meaning in both themes, so the
 * widget, the card and the status image read as one thing (Hawk,
 * 2026-10-21). 4x2 shows the first line of the Sanskrit and the plain
 * meaning; taller shows the whole card. The app sends two weeks of verses
 * ahead, so the widget turns over at midnight on its own, and only today's
 * verse is ever shown. Share opens the verse in the app, which draws the
 * status image.
 */
public class SubhashitaWidget extends BaseWidget {

    @Override
    protected RemoteViews render(Context context, int widthDp, int heightDp) {
        boolean large = heightDp >= 240;
        RemoteViews views = new RemoteViews(context.getPackageName(),
            large ? R.layout.widget_subhashita_large : R.layout.widget_subhashita);
        views.setOnClickPendingIntent(R.id.widget_root, Widgets.open(context, "/m/subhashita"));
        views.setOnClickPendingIntent(R.id.share, Widgets.open(context, "/m/subhashita"));

        JSONObject verse = WidgetStore.forToday(WidgetStore.get(context, "subhashita"), "days");
        if (verse == null) {
            views.setTextViewText(R.id.meaning, "A verse a day from the Bhagavad Gita, Chanakya Niti and the Puranas.");
            views.setTextViewText(R.id.source, "Open Siddha to load today’s verse");
            views.setViewVisibility(R.id.sanskrit, View.GONE);
            if (large) {
                views.setViewVisibility(R.id.english, View.GONE);
                views.setViewVisibility(R.id.meaning_label, View.GONE);
                views.setTextViewText(R.id.date, "");
            }
            return views;
        }
        String english = verse.optString("english");
        // Older app versions sent no meaning; the verse itself stands in.
        String meaning = verse.optString("meaning");
        views.setTextViewText(R.id.source, verse.optString("source") + " " + verse.optString("ref"));
        if (large) {
            views.setTextViewText(R.id.date, Widgets.longDate(verse.optString("date")));
            String sanskrit = verse.optString("sanskrit").trim();
            views.setTextViewText(R.id.sanskrit, sanskrit);
            views.setViewVisibility(R.id.sanskrit, sanskrit.isEmpty() ? View.GONE : View.VISIBLE);
            views.setTextViewText(R.id.english, "“" + english + "”");
            views.setViewVisibility(R.id.english, english.isEmpty() ? View.GONE : View.VISIBLE);
            views.setTextViewText(R.id.meaning, meaning);
            views.setViewVisibility(R.id.meaning_label, meaning.isEmpty() ? View.GONE : View.VISIBLE);
            views.setViewVisibility(R.id.meaning, meaning.isEmpty() ? View.GONE : View.VISIBLE);
            return views;
        }
        views.setTextViewText(R.id.meaning, meaning.isEmpty() ? "“" + english + "”" : meaning);
        // Where a launcher's two rows are short, two lines of meaning keep the source on the card.
        views.setInt(R.id.meaning, "setMaxLines", heightDp > 0 && heightDp < 150 ? 2 : 3);
        String line = firstLine(verse.optString("sanskrit"));
        views.setTextViewText(R.id.sanskrit, line);
        views.setViewVisibility(R.id.sanskrit, line.isEmpty() ? View.GONE : View.VISIBLE);
        return views;
    }

    /** The verse's first line, without the danda that ends it. */
    static String firstLine(String sanskrit) {
        String line = sanskrit == null ? "" : sanskrit.trim().split("\n", 2)[0];
        return line.replaceAll("[\\s।॥]+$", "").trim();
    }
}
