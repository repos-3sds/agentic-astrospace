package app.asksiddha.mobile.widgets;

import android.content.Intent;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import org.json.JSONObject;

/**
 * The app's side of the home-screen widgets. The app publishes what each
 * widget shows as a JSON "part" (today, calendar, subhashita, mantra); the
 * widgets draw from those parts without the app running. A widget tap that
 * opens a screen comes back as an "open" event with the route.
 */
@CapacitorPlugin(name = "SiddhaWidgets")
public class WidgetsPlugin extends Plugin {

    private static WidgetsPlugin instance;
    /** A route a widget asked for before the web layer was listening. */
    private static String pendingRoute;

    @Override
    public void load() {
        instance = this;
    }

    @PluginMethod
    public void publish(PluginCall call) {
        String part = call.getString("part");
        JSObject data = call.getObject("data");
        if (part == null || data == null) {
            call.reject("part and data are required");
            return;
        }
        WidgetStore.put(getContext(), part, data.toString());
        Widgets.refreshAll(getContext());
        call.resolve();
    }

    @PluginMethod
    public void takeMantraTaps(PluginCall call) {
        JSONObject taps = WidgetStore.takeMantraTaps(getContext());
        JSObject result = new JSObject();
        result.put("key", taps.optString("key", ""));
        result.put("date", taps.optString("date", ""));
        result.put("taps", taps.optInt("taps", 0));
        call.resolve(result);
    }

    @PluginMethod
    public void clear(PluginCall call) {
        WidgetStore.clear(getContext());
        Widgets.refreshAll(getContext());
        call.resolve();
    }

    /** The route a widget opened the app with, if the event was missed. */
    @PluginMethod
    public void takePendingRoute(PluginCall call) {
        JSObject result = new JSObject();
        result.put("route", pendingRoute == null ? "" : pendingRoute);
        pendingRoute = null;
        call.resolve(result);
    }

    /** Called by MainActivity for every intent; true when it came from a widget. */
    public static boolean handle(Intent intent) {
        if (intent == null) return false;
        String route = intent.getStringExtra(Widgets.EXTRA_ROUTE);
        if (route == null || !route.startsWith("/m/")) return false;
        intent.removeExtra(Widgets.EXTRA_ROUTE);
        if (instance == null) {
            pendingRoute = route;
            return true;
        }
        // Retained until the web layer adds its listener, so a cold start
        // from a widget still lands on the screen it asked for.
        JSObject event = new JSObject();
        event.put("route", route);
        instance.notifyListeners("open", event, true);
        return true;
    }
}
