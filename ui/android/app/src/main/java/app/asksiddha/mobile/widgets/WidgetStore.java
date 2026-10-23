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
        deleteListenAudio(context);
    }

    // ── Siddha's natural voice for the Listen widget ──

    private static final String LISTEN_AUDIO = "listen.audio";

    private static java.io.File listenDir(Context context) {
        return new java.io.File(context.getFilesDir(), "listen-audio");
    }

    private static void deleteListenAudio(Context context) {
        java.io.File[] files = listenDir(context).listFiles();
        if (files != null) for (java.io.File f : files) f.delete();
    }

    /** Replaces the stored audio; an empty list just removes it. */
    public static boolean saveListenAudio(Context context, String date, String text, java.util.List<byte[]> parts) {
        prefs(context).edit().remove(LISTEN_AUDIO).commit();
        deleteListenAudio(context);
        if (parts.isEmpty()) return true;
        java.io.File dir = listenDir(context);
        if (!dir.isDirectory() && !dir.mkdirs()) return false;
        for (int i = 0; i < parts.size(); i++) {
            try (java.io.FileOutputStream out = new java.io.FileOutputStream(new java.io.File(dir, "part-" + i + ".mp3"))) {
                out.write(parts.get(i));
            } catch (java.io.IOException e) {
                deleteListenAudio(context);
                return false;
            }
        }
        JSONObject manifest = new JSONObject();
        try {
            manifest.put("date", date);
            manifest.put("text", text);
            manifest.put("count", parts.size());
        } catch (JSONException e) {
            return false;
        }
        prefs(context).edit().putString(LISTEN_AUDIO, manifest.toString()).apply();
        return true;
    }

    /**
     * The natural-voice audio for this text today, in order; empty when there
     * is none, it is another day's, or the brief has changed since it was made.
     */
    public static java.util.List<java.io.File> listenAudio(Context context, String text) {
        java.util.List<java.io.File> files = new java.util.ArrayList<>();
        String raw = prefs(context).getString(LISTEN_AUDIO, null);
        if (raw == null) return files;
        try {
            JSONObject manifest = new JSONObject(raw);
            if (!today().equals(manifest.optString("date")) || !text.equals(manifest.optString("text"))) return files;
            for (int i = 0; i < manifest.optInt("count"); i++) {
                java.io.File f = new java.io.File(listenDir(context), "part-" + i + ".mp3");
                if (!f.isFile()) return new java.util.ArrayList<>();
                files.add(f);
            }
        } catch (JSONException e) {
            return new java.util.ArrayList<>();
        }
        return files;
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

    // ── Look: kept apart from the parts so signing out does not reset it ──

    private static final String LOOK = "siddha_widget_look";
    private static final String OPACITY = "card.opacity";
    /** How solid the widget card is, 0 (clear) to 100 (solid, the default). */
    public static int opacity(Context context) {
        return context.getApplicationContext().getSharedPreferences(LOOK, Context.MODE_PRIVATE)
            .getInt(OPACITY, 100);
    }

    public static void setOpacity(Context context, int percent) {
        int clamped = Math.max(0, Math.min(100, percent));
        context.getApplicationContext().getSharedPreferences(LOOK, Context.MODE_PRIVATE)
            .edit().putInt(OPACITY, clamped).apply();
    }
}
