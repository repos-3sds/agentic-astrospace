package app.asksiddha.mobile;

import android.app.NotificationChannel;
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

    /**
     * The WebView scales text by the system font size, up to 200%. The
     * designed screens hold up to about 130% (checked on Today, Ask, Calendar
     * and Explore); past that, names, signs and the month header clip and the
     * tab labels collide (regression pass, 2026-10-17). Font scale is not in
     * the manifest's configChanges, so a change recreates the activity and
     * this runs again.
     */
    static final int MAX_TEXT_ZOOM = 130;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(PushConfigPlugin.class);
        registerPlugin(WidgetsPlugin.class);
        super.onCreate(savedInstanceState);
        capTextZoom();
        createBellChannel();
        WidgetsPlugin.handle(getIntent());
        Widgets.refreshAll(this);
    }

    /** A widget tap while the app is already open (singleTask) lands here. */
    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        WidgetsPlugin.handle(intent);
    }

    private void capTextZoom() {
        if (getBridge() == null || getBridge().getWebView() == null) return;
        WebSettings settings = getBridge().getWebView().getSettings();
        int system = Math.round(getResources().getConfiguration().fontScale * 100);
        settings.setTextZoom(Math.min(system, MAX_TEXT_ZOOM));
    }

    /**
     * Android fixes a channel's sound when the channel is created, so it has
     * to exist before the first push arrives. Creating an existing channel is
     * a no-op, and the user can still change the sound in system settings.
     */
    private void createBellChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return;
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager == null) return;
        NotificationChannel channel = new NotificationChannel(
            BELL_CHANNEL_ID, "Siddha notifications", NotificationManager.IMPORTANCE_HIGH);
        channel.setDescription("Morning brief, window alerts and reminders");
        Uri sound = Uri.parse("android.resource://" + getPackageName() + "/" + R.raw.temple_bell);
        AudioAttributes attributes = new AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_NOTIFICATION)
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
            .build();
        channel.setSound(sound, attributes);
        manager.createNotificationChannel(channel);
    }
}
