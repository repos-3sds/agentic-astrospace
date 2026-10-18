package app.asksiddha.mobile.widgets;

import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.widget.RemoteViews;
import app.asksiddha.mobile.R;
import org.json.JSONObject;

/** Listen to your day: plays today's brief aloud without opening the app. */
public class ListenWidget extends BaseWidget {

    @Override
    protected RemoteViews render(Context context, int widthDp, int heightDp) {
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_listen);
        views.setOnClickPendingIntent(R.id.text, Widgets.open(context, "/m/today"));

        JSONObject today = WidgetStore.get(context, "today");
        boolean fresh = today != null && WidgetStore.today().equals(today.optString("date"))
            && !today.optString("listen").isEmpty();
        boolean speaking = WidgetStore.speaking(context);

        if (!fresh) {
            views.setImageViewResource(R.id.play, R.drawable.widget_ic_play);
            views.setTextViewText(R.id.title, "Listen to your day");
            views.setTextViewText(R.id.subtitle, "Open Siddha once today to load it");
            views.setOnClickPendingIntent(R.id.play, Widgets.open(context, "/m/today"));
            return views;
        }
        views.setImageViewResource(R.id.play, speaking ? R.drawable.widget_ic_stop : R.drawable.widget_ic_play);
        views.setTextViewText(R.id.title, speaking ? "Playing your day" : "Listen to your day");
        views.setTextViewText(R.id.subtitle, subtitle(today));
        views.setOnClickPendingIntent(R.id.play,
            speech(context, speaking ? BriefSpeechService.ACTION_STOP : BriefSpeechService.ACTION_PLAY));
        return views;
    }

    /** "Steady day · about 1 min": the brief's length at the 0.9x it is read at. */
    static String subtitle(JSONObject today) {
        String label = today.optString("label");
        String words = today.optString("listen").trim();
        int count = words.isEmpty() ? 0 : words.split("\\s+").length;
        // About 150 words a minute at normal speed, so 135 at 0.9x.
        long minutes = Math.max(1, Math.round(count / 135.0));
        String day = label.isEmpty() ? "Today" : label.endsWith("care") ? label : label + " day";
        return day + " · about " + minutes + " min";
    }

    static PendingIntent speech(Context context, String action) {
        Intent intent = new Intent(context, BriefSpeechService.class).setAction(action);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE;
        // A tap on a widget may start a foreground service from the background.
        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
            ? PendingIntent.getForegroundService(context, action.hashCode(), intent, flags)
            : PendingIntent.getService(context, action.hashCode(), intent, flags);
    }
}
