package app.asksiddha.mobile;

import android.content.ComponentName;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * Switches the launcher icon between the day and night galaxy to follow the
 * in-app theme. The manifest declares two activity-aliases, .LauncherDay and
 * .LauncherNight, both targeting MainActivity; exactly one is enabled.
 *
 * The swap is deferred until the app leaves the foreground: some launchers
 * close an app whose launcher component changes under it, and doing it in
 * onStop means the reader never sees that. The wanted icon is persisted, so a
 * process killed before onStop still applies it on the next stop.
 */
@CapacitorPlugin(name = "AppIcon")
public class AppIconPlugin extends Plugin {

    private static final String PREFS = "siddha_app_icon";
    private static final String KEY = "wanted";

    @PluginMethod
    public void set(PluginCall call) {
        boolean dark = Boolean.TRUE.equals(call.getBoolean("dark", true));
        prefs().edit().putString(KEY, dark ? "night" : "day").apply();
        call.resolve();
    }

    @Override
    protected void handleOnStop() {
        super.handleOnStop();
        apply(getContext());
    }

    private SharedPreferences prefs() {
        return getContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private void apply(Context context) {
        String wanted = prefs().getString(KEY, null);
        if (wanted == null) return;
        boolean day = "day".equals(wanted);
        String pkg = context.getPackageName();
        PackageManager pm = context.getPackageManager();
        ComponentName dayAlias = new ComponentName(pkg, pkg + ".LauncherDay");
        ComponentName nightAlias = new ComponentName(pkg, pkg + ".LauncherNight");
        // Enable the new entry before disabling the old one so the launcher is
        // never left without an icon for the app.
        setEnabled(pm, day ? dayAlias : nightAlias, true);
        setEnabled(pm, day ? nightAlias : dayAlias, false);
    }

    private static void setEnabled(PackageManager pm, ComponentName component, boolean enabled) {
        int state = enabled
            ? PackageManager.COMPONENT_ENABLED_STATE_ENABLED
            : PackageManager.COMPONENT_ENABLED_STATE_DISABLED;
        if (pm.getComponentEnabledSetting(component) == state) return;
        pm.setComponentEnabledSetting(component, state, PackageManager.DONT_KILL_APP);
    }
}
