package app.asksiddha.mobile;

import android.content.Context;
import android.content.SharedPreferences;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * Settings > Text size: the reader's own text size for Siddha only, leaving
 * the phone's font setting alone for every other app. 0 means "follow the
 * phone" (up to MainActivity.MAX_TEXT_ZOOM). Stored natively, not in the web
 * layer, so MainActivity applies it before the first screen draws.
 */
@CapacitorPlugin(name = "TextSize")
public class TextSizePlugin extends Plugin {

    static final String PREFS = "siddha_text_size";
    static final String KEY = "percent";
    /** The sizes Settings offers; the designed screens hold up to about 130%. */
    static final int MIN = 85;
    static final int MAX = 130;

    /** The reader's choice, or 0 to follow the phone. */
    static int chosen(Context context) {
        int percent = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getInt(KEY, 0);
        return percent >= MIN && percent <= MAX ? percent : 0;
    }

    @PluginMethod
    public void get(PluginCall call) {
        JSObject result = new JSObject();
        result.put("percent", chosen(getContext()));
        result.put("phonePercent", Math.round(getContext().getResources().getConfiguration().fontScale * 100));
        call.resolve(result);
    }

    @PluginMethod
    public void set(PluginCall call) {
        int percent = call.getInt("percent", 0);
        if (percent != 0 && (percent < MIN || percent > MAX)) {
            call.reject("Text size must be 0 or between " + MIN + " and " + MAX);
            return;
        }
        SharedPreferences.Editor editor = getContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit();
        if (percent == 0) editor.remove(KEY); else editor.putInt(KEY, percent);
        editor.apply();
        if (getActivity() == null) {
            call.resolve();
            return;
        }
        getActivity().runOnUiThread(() -> {
            if (getActivity() instanceof MainActivity) ((MainActivity) getActivity()).applyTextZoom();
            JSObject result = new JSObject();
            result.put("percent", percent);
            call.resolve(result);
        });
    }
}
