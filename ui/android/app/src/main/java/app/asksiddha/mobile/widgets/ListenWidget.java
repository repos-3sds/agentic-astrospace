package app.asksiddha.mobile.widgets;

import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.widget.RemoteViews;
import app.asksiddha.mobile.R;
import org.json.JSONObject;

/**
 * Listen to your day: plays today's brief aloud without opening the app.
 * A 2x2 square by default with a big play button; wider, today's headline
 * sits beside the button; squashed to one row, it is the slim bar.
 */
public class ListenWidget extends BaseWidget {

    private enum Shape { BAR, SQUARE, WIDE }

    @Override
    protected RemoteViews render(Context context, int widthDp, int heightDp) {
        Shape shape = heightDp > 0 && heightDp < 100 ? Shape.BAR : widthDp >= 200 ? Shape.WIDE : Shape.SQUARE;
        RemoteViews views = new RemoteViews(context.getPackageName(),
            shape == Shape.BAR ? R.layout.widget_listen
                : shape == Shape.WIDE ? R.layout.widget_listen_wide : R.layout.widget_listen_square);
        views.setOnClickPendingIntent(R.id.text, Widgets.open(context, "/m/today"));

        JSONObject today = WidgetStore.get(context, "today");
        boolean fresh = today != null && WidgetStore.today().equals(today.optString("date"))
            && !today.optString("listen").isEmpty();
        // The stored flag outlives a killed process; only a live service is reading.
        boolean speaking = WidgetStore.speaking(context) && BriefSpeechService.isRunning();
        if (WidgetStore.speaking(context) && !speaking) WidgetStore.setSpeaking(context, false);

        if (!fresh) {
            views.setImageViewResource(R.id.play, R.drawable.widget_ic_play);
            views.setOnClickPendingIntent(R.id.play, Widgets.open(context, "/m/today"));
            views.setContentDescription(R.id.play, "Open Siddha to load today's reading");
            switch (shape) {
                case SQUARE:
                    views.setTextViewText(R.id.title, "Open Siddha");
                    views.setTextViewText(R.id.subtitle, "to load today’s reading");
                    break;
                case WIDE:
                    views.setTextViewText(R.id.title, "Listen to your day");
                    views.setTextViewText(R.id.headline, "Open Siddha once today to load it");
                    views.setTextViewText(R.id.subtitle, "");
                    break;
                default:
                    views.setTextViewText(R.id.title, "Listen to your day");
                    views.setTextViewText(R.id.subtitle, "Open Siddha once today to load it");
            }
            return views;
        }
        views.setImageViewResource(R.id.play, speaking ? R.drawable.widget_ic_stop : R.drawable.widget_ic_play);
        switch (shape) {
            case SQUARE:
                views.setTextViewText(R.id.title, speaking ? "Playing now" : dayLabel(today));
                views.setTextViewText(R.id.subtitle, "About " + minutes(today) + " min");
                break;
            case WIDE:
                views.setTextViewText(R.id.title, speaking ? "Playing your day" : "Listen to your day");
                views.setTextViewText(R.id.headline, today.optString("headline"));
                views.setTextViewText(R.id.subtitle, subtitle(today));
                break;
            default:
                views.setTextViewText(R.id.title, speaking ? "Playing your day" : "Listen to your day");
                views.setTextViewText(R.id.subtitle, subtitle(today));
        }
        views.setOnClickPendingIntent(R.id.play,
            speech(context, BriefSpeechService.ACTION_TOGGLE));
        // The play button is the widget's only control; TalkBack read it as "unlabelled".
        views.setContentDescription(R.id.play, speaking ? "Stop reading" : "Play today's reading");
        return views;
    }

    /** "Steady day · about 1 min": the brief's length at the 0.9x it is read at. */
    static String subtitle(JSONObject today) {
        return dayLabel(today) + " · about " + minutes(today) + " min";
    }

    /** "Steady day", or the label itself when it already reads whole ("Take care"). */
    static String dayLabel(JSONObject today) {
        String label = today.optString("label");
        return label.isEmpty() ? "Today" : label.endsWith("care") ? label : label + " day";
    }

    static long minutes(JSONObject today) {
        String words = today.optString("listen").trim();
        int count = words.isEmpty() ? 0 : words.split("\\s+").length;
        // About 150 words a minute at normal speed, so 135 at 0.9x.
        return Math.max(1, Math.round(count / 135.0));
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
