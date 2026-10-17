package app.asksiddha.mobile.widgets;

import android.content.Context;
import android.widget.RemoteViews;
import app.asksiddha.mobile.R;

/** A search bar that opens Ask. */
public class AskWidget extends BaseWidget {

    @Override
    protected RemoteViews render(Context context, int widthDp, int heightDp) {
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_ask);
        views.setOnClickPendingIntent(R.id.widget_root, Widgets.open(context, "/m/ask"));
        return views;
    }
}
