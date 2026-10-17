package app.asksiddha.mobile.widgets;

import android.content.Context;
import android.widget.RemoteViews;
import app.asksiddha.mobile.R;
import org.json.JSONObject;

/**
 * Today's Subhashita. The app sends two weeks of verses ahead, so the widget
 * turns over at midnight on its own. Only today's verse is ever shown. The
 * share button opens the verse in the app, which draws the status image.
 */
public class SubhashitaWidget extends BaseWidget {

    @Override
    protected RemoteViews render(Context context, int widthDp, int heightDp) {
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_subhashita);
        views.setOnClickPendingIntent(R.id.widget_root, Widgets.open(context, "/m/subhashita"));
        views.setOnClickPendingIntent(R.id.share, Widgets.open(context, "/m/subhashita"));

        JSONObject verse = WidgetStore.forToday(WidgetStore.get(context, "subhashita"), "days");
        if (verse == null) {
            views.setTextViewText(R.id.english, "A verse a day from the Bhagavad Gita, Chanakya Niti and the Puranas.");
            views.setTextViewText(R.id.source, "Open Siddha to load today’s verse");
            return views;
        }
        views.setTextViewText(R.id.english, "“" + verse.optString("english") + "”");
        views.setTextViewText(R.id.source, "— " + verse.optString("source") + " " + verse.optString("ref"));
        return views;
    }
}
