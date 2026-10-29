package app.asksiddha.mobile;

import android.app.NotificationChannel;
import android.app.UiModeManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ActivityInfo;
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
    /** Panchang alarms set to ring: the alarm stream, so silent mode does not mute them. */
    static final String ALARM_CHANNEL_ID = "siddha_alarm";
    /** Panchang alarms set to silent, and "it has ended" notes: on screen, no sound. */
    static final String QUIET_CHANNEL_ID = "siddha_quiet";

    /**
     * The WebView scales text by the system font size, up to 200%. The
     * designed screens hold up to about 130% (checked on Today, Ask, Calendar
     * and Explore); past that, names, signs and the month header clip and the
     * tab labels collide (regression pass, 2026-10-17). Hawk chose 115%
     * (2026-10-20) so the screens keep their designed look, then 102%
     * (2026-10-24) after testers' 360-wide phones at 115% showed every screen
     * about 1.3x larger than designed. Headlines ignore the setting entirely
     * (m-display-size in mobile-tokens.scss). The home-screen widgets use the
     * same cap (Widgets.capText). A reader who wants another size for Siddha
     * alone sets it in Settings > Text size (TextSizePlugin), which replaces
     * the phone's setting here. Font scale is not in the manifest's
     * configChanges, so a change recreates the activity and this runs again.
     */
    public static final int MAX_TEXT_ZOOM = 102;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(PushConfigPlugin.class);
        registerPlugin(WidgetsPlugin.class);
        registerPlugin(NativeCalendarPlugin.class);
        registerPlugin(InAppReviewPlugin.class);
        registerPlugin(InAppUpdatePlugin.class);
        registerPlugin(TextSizePlugin.class);
        super.onCreate(savedInstanceState);
        holdPhonesUpright();
        matchLaunchScreenToTheme();
        applyTextZoom();
        createChannels();
        WidgetsPlugin.handle(getIntent());
        Widgets.refreshAll(this);
    }

    /**
     * Phones stay in portrait, as on iPhone; the phone screens were drawn for
     * it. Tablets (600dp and wider at their narrowest) turn freely and get the
     * tablet layout. Android 16 ignores a lock on large screens anyway, so
     * this is the only place it could apply.
     */
    private void holdPhonesUpright() {
        if (getResources().getConfiguration().smallestScreenWidthDp < 600) {
            setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT);
        }
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

    void applyTextZoom() {
        if (getBridge() == null || getBridge().getWebView() == null) return;
        WebSettings settings = getBridge().getWebView().getSettings();
        int chosen = TextSizePlugin.chosen(this);
        int system = Math.round(getResources().getConfiguration().fontScale * 100);
        settings.setTextZoom(chosen != 0 ? chosen : Math.min(system, MAX_TEXT_ZOOM));
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
        manager.createNotificationChannel(alarmChannel());
        NotificationChannel quiet = new NotificationChannel(
            QUIET_CHANNEL_ID, "Quiet panchang alarms", NotificationManager.IMPORTANCE_LOW);
        quiet.setDescription("Timings you chose to see without a sound");
        quiet.setSound(null, null);
        manager.createNotificationChannel(quiet);
    }

    /**
     * The "Alarm" style: thirty seconds of temple bell on the alarm stream,
     * which plays when the ringer is on silent and is let through by Do Not
     * Disturb wherever alarms are. Bypassing DND outright is left to the user.
     */
    private NotificationChannel alarmChannel() {
        NotificationChannel channel = new NotificationChannel(
            ALARM_CHANNEL_ID, "Panchang alarms", NotificationManager.IMPORTANCE_HIGH);
        channel.setDescription("Timings you chose to ring like an alarm, such as Brahma Muhurta");
        Uri sound = Uri.parse("android.resource://" + getPackageName() + "/" + R.raw.alarm_bell);
        AudioAttributes attributes = new AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_ALARM)
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
            .build();
        channel.setSound(sound, attributes);
        channel.enableVibration(true);
        return channel;
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
