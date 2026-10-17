package app.asksiddha.mobile.widgets;

import android.content.Context;
import android.content.SharedPreferences;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * What the home-screen widgets draw from. The app writes one JSON part per
 * subject ("today", "calendar", "subhashita", "mantra") through
 * {@link WidgetsPlugin}; the widgets only read. Nothing here goes to the
 * network: a widget shows what the app last saw, and says so when that is
 * not today.
 */
public final class WidgetStore {

    private static final String PREFS = "siddha_widgets";
    private static final String PART = "part.";
    private static final String MANTRA_TAPS = "mantra.taps";
    private static final String SPEAKING = "listen.speaking";

    private WidgetStore() {}

    private static SharedPreferences prefs(Context context) {
        return context.getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public static void put(Context context, String part, String json) {
        prefs(context).edit().putString(PART + part, json).apply();
    }

    /** The part as last published, or null when the app has not sent it yet. */
    public static JSONObject get(Context context, String part) {
        String raw = prefs(context).getString(PART + part, null);
        if (raw == null) return null;
        try {
            return new JSONObject(raw);
        } catch (JSONException e) {
            return null;
        }
    }

    /** Signing out must not leave the last account's day on the home screen. */
    public static void clear(Context context) {
        prefs(context).edit().clear().apply();
    }

    /** The phone's own calendar day, the same YYYY-MM-DD the app uses. */
    public static String today() {
        return new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(new Date());
    }

    /** The row of `days` whose "date" is today, if the app sent one. */
    public static JSONObject forToday(JSONObject part, String key) {
        if (part == null) return null;
        JSONArray days = part.optJSONArray(key);
        if (days == null) return null;
        String today = today();
        for (int i = 0; i < days.length(); i++) {
            JSONObject row = days.optJSONObject(i);
            if (row != null && today.equals(row.optString("date"))) return row;
        }
        return null;
    }

    // ── Mantra taps made on the widget, waiting for the app to fold them in ──

    /** Counts one tap for the practice and day; returns the new pending total. */
    public static int addMantraTap(Context context, String key, String date) {
        JSONObject taps = pendingTaps(context);
        int count = 1;
        if (key.equals(taps.optString("key")) && date.equals(taps.optString("date"))) {
            count = taps.optInt("taps", 0) + 1;
        }
        try {
            JSONObject next = new JSONObject();
            next.put("key", key);
            next.put("date", date);
            next.put("taps", count);
            prefs(context).edit().putString(MANTRA_TAPS, next.toString()).apply();
        } catch (JSONException ignored) {
            // put() with a non-null key and a plain value cannot throw.
        }
        return count;
    }

    /** Hands the pending taps to the app and forgets them. */
    public static JSONObject takeMantraTaps(Context context) {
        JSONObject taps = pendingTaps(context);
        prefs(context).edit().remove(MANTRA_TAPS).apply();
        return taps;
    }

    private static JSONObject pendingTaps(Context context) {
        String raw = prefs(context).getString(MANTRA_TAPS, null);
        if (raw == null) return new JSONObject();
        try {
            return new JSONObject(raw);
        } catch (JSONException e) {
            return new JSONObject();
        }
    }

    // ── Listen ──

    public static boolean speaking(Context context) {
        return prefs(context).getBoolean(SPEAKING, false);
    }

    public static void setSpeaking(Context context, boolean speaking) {
        prefs(context).edit().putBoolean(SPEAKING, speaking).apply();
    }
}
