package app.asksiddha.mobile;

import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.provider.CalendarContract;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * Opens the phone's own calendar on a filled-in "new event" form (audit N18).
 *
 * The web layer used to send Android readers to a calendar.google.com link,
 * which opens the Google Calendar app only when it is installed and claims the
 * link; on a Samsung with Samsung Calendar it landed in the browser. ACTION_INSERT
 * is answered by whichever calendar app the phone uses, and the reader still
 * presses Save, so the app needs no calendar permission.
 *
 * insert({ title, description?, location?, begin, end, allDay }): begin and end
 * are epoch milliseconds; for an all-day event they are UTC midnights, end
 * exclusive, as CalendarContract expects. Rejects with "unavailable" when no
 * calendar app answers, so the caller can fall back to the link.
 */
@CapacitorPlugin(name = "NativeCalendar")
public class NativeCalendarPlugin extends Plugin {

    @PluginMethod
    public void insert(PluginCall call) {
        String title = call.getString("title");
        Double begin = call.getDouble("begin");
        Double end = call.getDouble("end");
        if (title == null || begin == null || end == null) {
            call.reject("title, begin and end are required");
            return;
        }
        Intent intent = new Intent(Intent.ACTION_INSERT)
            .setData(CalendarContract.Events.CONTENT_URI)
            .putExtra(CalendarContract.Events.TITLE, title)
            .putExtra(CalendarContract.EXTRA_EVENT_BEGIN_TIME, begin.longValue())
            .putExtra(CalendarContract.EXTRA_EVENT_END_TIME, end.longValue())
            .putExtra(CalendarContract.EXTRA_EVENT_ALL_DAY, Boolean.TRUE.equals(call.getBoolean("allDay", false)));
        String description = call.getString("description");
        if (description != null) intent.putExtra(CalendarContract.Events.DESCRIPTION, description);
        String location = call.getString("location");
        if (location != null) intent.putExtra(CalendarContract.Events.EVENT_LOCATION, location);
        try {
            getActivity().startActivity(intent);
            call.resolve();
        } catch (ActivityNotFoundException e) {
            call.reject("unavailable");
        }
    }
}
