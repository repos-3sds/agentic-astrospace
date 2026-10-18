package app.asksiddha.mobile.widgets;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/**
 * Redraws the widgets when their words change on their own: midnight, a
 * timing window starting or ending (see Widgets.scheduleNextRefresh), the
 * phone's clock, timezone or language changing, and after a reboot. The
 * minute tick redraws only the countdowns.
 */
public class WidgetRefreshReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (Widgets.ACTION_TICK.equals(intent.getAction())) Widgets.tick(context);
        else Widgets.refreshAll(context);
    }
}
