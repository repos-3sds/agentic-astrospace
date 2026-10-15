package app.astrospace.mobile;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * Tells the web layer whether this build can register for push.
 *
 * The push plugin's register() calls FirebaseMessaging.getInstance() on a
 * background thread, and without google-services.json there is no default
 * FirebaseApp, so it throws and takes the whole process down. JavaScript
 * cannot catch that. The google-services Gradle plugin writes the
 * `google_app_id` string resource only when the file is present, so its
 * existence is the same signal Firebase itself relies on.
 */
@CapacitorPlugin(name = "PushConfig")
public class PushConfigPlugin extends Plugin {

    @PluginMethod
    public void available(PluginCall call) {
        int id = getContext().getResources().getIdentifier("google_app_id", "string", getContext().getPackageName());
        JSObject result = new JSObject();
        result.put("available", id != 0);
        call.resolve(result);
    }
}
