package app.asksiddha.mobile;

import android.app.NotificationChannel;
import android.app.UiModeManager;
import android.content.Context;
import android.content.Intent;
import android.app.NotificationManager;
import android.media.AudioAttributes;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.webkit.WebSettings;
import app.asksiddha.mobile.widgets.Widgets;
import app.asksiddha.mobile.widgets.WidgetsPlugin;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    /** Must match the server (astrospace/notifications/push.py) and the manifest default. */
    static final String BELL_CHANNEL_ID = "siddha_bell";
    /** Window alerts come several times a day: their own channel, at default
     * importance, so a reader can quiet them and keep the morning reading (N12). */
    static final String WINDOWS_CHANNEL_ID = "siddha_windows";

    /**
     * The WebView scales text by the system font size, up to 200%. The
     * designed screens hold up to about 130% (checked on Today, Ask, Calendar
     * and Explore); past that, names, signs and the month header clip and the
     * tab labels collide (regression pass, 2026-10-17). Hawk chose 115%
     * (2026-10-20) so the screens keep their designed look; the home-screen
     * widgets use the same cap (Widgets.capText). Font scale is not in
     * the manifest's configChanges, so a change recreates the activity and
     * this runs again.
     */
    public static final int MAX_TEXT_ZOOM = 115;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(PushConfigPlugin.class);
        registerPlugin(WidgetsPlugin.class);
        super.onCreate(savedInstanceState);
        matchLaunchScreenToTheme();
        capTextZoom();
        createChannels();
        WidgetsPlugin.handle(getIntent());
        Widgets.refreshAll(this);
    }

    /** A widget tap while the app is already open (singleTask) lands here. */
    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        WidgetsPlugin.handle(intent);
    }

    @Override
    public void onPause() {
        super.onPause();
        // The reader may have changed the theme in this visit; the next
        // launch screen should already show it.
        matchLaunchScreenToTheme();
    }

    /**
     * Android draws the launch screen before the app runs, in the phone's
     * light or dark mode. A light-themed app on a dark phone opened on black
     * and then faded to the ivory splash. ThemeService stores the reader's
     * choice under this key; from Android 12 the system uses the app's own
     * night mode for the launch screen.
     */
    private void matchLaunchScreenToTheme() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) return;
        UiModeManager modes = (UiModeManager) getSystemService(Context.UI_MODE_SERVICE);
        if (modes == null) return;
        String theme = getSharedPreferences("CapacitorStorage", MODE_PRIVATE).getString("astrospace-theme", "system");
        int mode = "light".equals(theme) ? UiModeManager.MODE_NIGHT_NO
            : "dark".equals(theme) ? UiModeManager.MODE_NIGHT_YES
            : UiModeManager.MODE_NIGHT_AUTO;
        modes.setApplicationNightMode(mode);
    }

    private void capTextZoom() {
        if (getBridge() == null || getBridge().getWebView() == null) return;
        WebSettings settings = getBridge().getWebView().getSettings();
        int system = Math.round(getResources().getConfiguration().fontScale * 100);
        settings.setTextZoom(Math.min(system, MAX_TEXT_ZOOM));
    }

    /**
     * Android fixes a channel's sound and importance when the channel is
     * created, so each has to exist before the first push arrives. Creating
     * an existing channel only updates its name and description, and the
     * user can still change the sound in system settings. siddha_bell keeps
     * its id: it is the manifest default, which older builds and any unknown
     * channel fall back to.
     */
    private void createChannels() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return;
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager == null) return;
        manager.createNotificationChannel(belled(
            BELL_CHANNEL_ID, "Daily reading and verse", NotificationManager.IMPORTANCE_HIGH,
            "Your morning reading and today's Subhashita"));
        manager.createNotificationChannel(belled(
            WINDOWS_CHANNEL_ID, "Good and careful times", NotificationManager.IMPORTANCE_DEFAULT,
            "A heads-up before a good or careful window in your day"));
    }

    private NotificationChannel belled(String id, String name, int importance, String description) {
        NotificationChannel channel = new NotificationChannel(id, name, importance);
        channel.setDescription(description);
        Uri sound = Uri.parse("android.resource://" + getPackageName() + "/" + R.raw.temple_bell);
        AudioAttributes attributes = new AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_NOTIFICATION)
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
            .build();
        channel.setSound(sound, attributes);
        return channel;
    }
}
