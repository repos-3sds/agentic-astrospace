package app.asksiddha.mobile;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.google.android.play.core.appupdate.AppUpdateInfo;
import com.google.android.play.core.appupdate.AppUpdateManager;
import com.google.android.play.core.appupdate.AppUpdateManagerFactory;
import com.google.android.play.core.appupdate.AppUpdateOptions;
import com.google.android.play.core.install.model.AppUpdateType;
import com.google.android.play.core.install.model.UpdateAvailability;

/**
 * Google Play's own update screen (core/app-update.service.ts).
 *
 * check() says whether Play has a newer build for this reader, on the track
 * they are on, so the app never offers an update Play cannot give yet (a
 * build still in Play's review, or an install not from Play). start() runs
 * Play's full-screen update, which downloads, installs and restarts the app.
 * When Play cannot start it, the app opens the Play listing instead; neither
 * is an error the reader should see.
 */
@CapacitorPlugin(name = "InAppUpdate")
public class InAppUpdatePlugin extends Plugin {

    private AppUpdateManager manager() {
        return AppUpdateManagerFactory.create(getContext());
    }

    @PluginMethod
    public void check(PluginCall call) {
        manager().getAppUpdateInfo().addOnCompleteListener(task -> {
            JSObject result = new JSObject();
            if (!task.isSuccessful()) {
                call.reject("Play could not say");
                return;
            }
            AppUpdateInfo info = task.getResult();
            int availability = info.updateAvailability();
            result.put("available", availability == UpdateAvailability.UPDATE_AVAILABLE
                || availability == UpdateAvailability.DEVELOPER_TRIGGERED_UPDATE_IN_PROGRESS);
            result.put("versionCode", info.availableVersionCode());
            result.put("immediate", info.isUpdateTypeAllowed(AppUpdateType.IMMEDIATE));
            call.resolve(result);
        });
    }

    @PluginMethod
    public void start(PluginCall call) {
        AppUpdateManager manager = manager();
        manager.getAppUpdateInfo().addOnCompleteListener(task -> {
            if (!task.isSuccessful() || getActivity() == null) {
                resolve(call, false);
                return;
            }
            AppUpdateInfo info = task.getResult();
            int availability = info.updateAvailability();
            boolean ready = availability == UpdateAvailability.UPDATE_AVAILABLE
                || availability == UpdateAvailability.DEVELOPER_TRIGGERED_UPDATE_IN_PROGRESS;
            if (!ready || !info.isUpdateTypeAllowed(AppUpdateType.IMMEDIATE)) {
                resolve(call, false);
                return;
            }
            manager.startUpdateFlow(info, getActivity(), AppUpdateOptions.defaultOptions(AppUpdateType.IMMEDIATE))
                .addOnCompleteListener(flow -> resolve(call, flow.isSuccessful()));
        });
    }

    private static void resolve(PluginCall call, boolean started) {
        JSObject result = new JSObject();
        result.put("started", started);
        call.resolve(result);
    }
}
