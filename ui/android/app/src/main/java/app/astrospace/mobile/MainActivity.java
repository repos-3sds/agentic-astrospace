package app.astrospace.mobile;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.media.AudioAttributes;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    /** Must match the server (astrospace/notifications/push.py) and the manifest default. */
    static final String BELL_CHANNEL_ID = "siddha_bell";

    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(PushConfigPlugin.class);
        super.onCreate(savedInstanceState);
        createBellChannel();
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
