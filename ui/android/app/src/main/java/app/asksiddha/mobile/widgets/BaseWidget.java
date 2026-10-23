package app.asksiddha.mobile.widgets;

import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.Context;
import android.os.Bundle;
import android.widget.RemoteViews;

/**
 * Every Siddha widget draws itself from {@link WidgetStore} in one place,
 * {@link #render}, for the size it has been given. Size is read from the
 * widget's options rather than from Android 12's size map, so the same code
 * covers every phone back to Android 7 (minSdk 24).
 */
public abstract class BaseWidget extends AppWidgetProvider {

    /** The widget for its current size, in dp. */
    protected abstract RemoteViews render(Context context, int widthDp, int heightDp);

    @Override
    public void onUpdate(Context context, AppWidgetManager manager, int[] ids) {
        for (int id : ids) draw(context, manager, id);
        Widgets.scheduleNextRefresh(context);
    }

    @Override
    public void onAppWidgetOptionsChanged(Context context, AppWidgetManager manager, int id, Bundle options) {
        draw(context, manager, id);
    }

    void draw(Context context, AppWidgetManager manager, int id) {
        Bundle options = manager.getAppWidgetOptions(id);
        // MIN_WIDTH is the portrait width and MAX_HEIGHT the portrait height:
        // the size the widget actually has on a phone held upright.
        int width = options.getInt(AppWidgetManager.OPTION_APPWIDGET_MIN_WIDTH, 0);
        int height = options.getInt(AppWidgetManager.OPTION_APPWIDGET_MAX_HEIGHT, 0);
        try {
            manager.updateAppWidget(id, Widgets.applyOpacity(context, Widgets.capText(context, render(context, width, height))));
        } catch (RuntimeException e) {
            // A widget that cannot draw keeps its last picture; the app is unaffected.
            android.util.Log.w("SiddhaWidgets", "could not draw " + getClass().getSimpleName(), e);
        }
    }
}
