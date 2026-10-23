package app.asksiddha.mobile.widgets;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.ServiceInfo;
import android.media.AudioAttributes;
import android.media.AudioFocusRequest;
import android.media.AudioManager;
import android.media.MediaPlayer;
import android.os.Build;
import android.os.Bundle;
import android.os.IBinder;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import androidx.core.content.ContextCompat;
import app.asksiddha.mobile.R;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import org.json.JSONObject;

/**
 * Reads today's brief aloud from the Listen widget. In Siddha's natural voice
 * when the app has saved today's audio for it (WidgetBridgeService
 * .publishListenAudio: Plus readers who haven't chosen a phone voice);
 * otherwise with the phone's own voice, at the same 0.9x the Listen sheet uses. A media-playback
 * foreground service, so it keeps speaking with the screen off and shows a
 * notification with Stop while it does.
 *
 * The text is the one the app's Listen sheet reads (the agent's spoken
 * script when there is one), sent with the "today" part.
 *
 * It behaves like any other player: it takes transient audio focus, so music
 * pauses while it speaks and resumes after, and it stops for a call, for
 * another app taking focus, and when headphones are unplugged.
 */
public class BriefSpeechService extends Service implements TextToSpeech.OnInitListener {

    static final String ACTION_STOP = "app.asksiddha.mobile.widgets.LISTEN_STOP";
    /**
     * The widget's button: stop if this service is reading, else play. The
     * service decides, not the widget's last picture, which can be stale: a
     * redraw after the process was killed mid-reading (a resize does one)
     * showed Stop with nothing playing, so the tap did nothing (Hawk,
     * 2026-10-23).
     */
    static final String ACTION_TOGGLE = "app.asksiddha.mobile.widgets.LISTEN_TOGGLE";

    /** True from a play until onDestroy, in this process only, so a killed process reads false. */
    private static volatile boolean running;

    static boolean isRunning() {
        return running;
    }
    private static final String CHANNEL_ID = "siddha_listen";
    private static final int NOTIFICATION_ID = 4201;
    private static final float RATE = 0.9f;

    private static final AudioAttributes SPEECH = new AudioAttributes.Builder()
        .setUsage(AudioAttributes.USAGE_MEDIA)
        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
        .build();

    private TextToSpeech tts;
    private MediaPlayer player;
    private List<File> natural = new ArrayList<>();
    private List<String> chunks = new ArrayList<>();
    private AudioManager audio;
    private AudioFocusRequest focusRequest;
    private boolean noisyRegistered;

    private final AudioManager.OnAudioFocusChangeListener focusListener = change -> {
        // A call, an alarm or another player: stop rather than talk over it.
        if (change == AudioManager.AUDIOFOCUS_LOSS || change == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT) stopSelf();
    };

    private final BroadcastReceiver noisy = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            if (AudioManager.ACTION_AUDIO_BECOMING_NOISY.equals(intent.getAction())) stopSelf();
        }
    };

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? null : intent.getAction();
        // startForeground must follow a foreground-service start promptly, even
        // when the answer is to stop at once.
        startInForeground();
        if (ACTION_STOP.equals(action) || (ACTION_TOGGLE.equals(action) && running)) {
            stopSelf();
            return START_NOT_STICKY;
        }
        JSONObject today = WidgetStore.get(this, "today");
        String text = today == null || !WidgetStore.today().equals(today.optString("date"))
            ? "" : today.optString("listen");
        if (text.isEmpty()) {
            stopSelf();
            return START_NOT_STICKY;
        }
        chunks = split(text, TextToSpeech.getMaxSpeechInputLength() - 100);
        natural = WidgetStore.listenAudio(this, text);
        running = true;
        WidgetStore.setSpeaking(this, true);
        Widgets.refresh(this, ListenWidget.class);
        if (!natural.isEmpty()) {
            if (!requestFocus()) {
                stopSelf();
                return START_NOT_STICKY;
            }
            playNatural(0);
        } else if (tts == null) {
            tts = new TextToSpeech(getApplicationContext(), this);
        } else {
            speak();
        }
        return START_NOT_STICKY;
    }

    @Override
    public void onInit(int status) {
        if (status != TextToSpeech.SUCCESS || tts == null) {
            stopSelf();
            return;
        }
        Locale india = new Locale("en", "IN");
        if (tts.isLanguageAvailable(india) < TextToSpeech.LANG_AVAILABLE) india = Locale.ENGLISH;
        tts.setLanguage(india);
        tts.setSpeechRate(RATE);
        tts.setAudioAttributes(SPEECH);
        tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
            @Override public void onStart(String id) {}
            @Override public void onDone(String id) {
                if (String.valueOf(chunks.size() - 1).equals(id)) stopSelf();
            }
            @Override @Deprecated public void onError(String id) { stopSelf(); }
        });
        speak();
    }

    /** Plays the saved pieces in order; a piece that won't play falls back to the phone voice. */
    private void playNatural(int index) {
        releasePlayer();
        if (index >= natural.size()) {
            stopSelf();
            return;
        }
        MediaPlayer next = new MediaPlayer();
        player = next;
        try {
            next.setAudioAttributes(SPEECH);
            next.setDataSource(natural.get(index).getAbsolutePath());
            next.setOnCompletionListener(done -> playNatural(index + 1));
            next.setOnErrorListener((mp, what, extra) -> {
                fallBackToPhoneVoice();
                return true;
            });
            next.prepare();
            next.start();
        } catch (IOException | RuntimeException e) {
            fallBackToPhoneVoice();
        }
    }

    private void fallBackToPhoneVoice() {
        releasePlayer();
        natural = new ArrayList<>();
        if (tts == null) {
            tts = new TextToSpeech(getApplicationContext(), this);
        } else {
            speak();
        }
    }

    private void releasePlayer() {
        if (player == null) return;
        try {
            player.release();
        } catch (RuntimeException ignored) {
            // Already released.
        }
        player = null;
    }

    private void speak() {
        if (!requestFocus()) {
            stopSelf();
            return;
        }
        tts.stop();
        for (int i = 0; i < chunks.size(); i++) {
            tts.speak(chunks.get(i), i == 0 ? TextToSpeech.QUEUE_FLUSH : TextToSpeech.QUEUE_ADD,
                new Bundle(), String.valueOf(i));
        }
    }

    private boolean requestFocus() {
        if (audio == null) audio = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
        if (audio == null) return true;
        if (!noisyRegistered) {
            ContextCompat.registerReceiver(this, noisy,
                new IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY), ContextCompat.RECEIVER_NOT_EXPORTED);
            noisyRegistered = true;
        }
        int result;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            if (focusRequest == null) {
                focusRequest = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
                    .setAudioAttributes(SPEECH)
                    .setOnAudioFocusChangeListener(focusListener)
                    .build();
            }
            result = audio.requestAudioFocus(focusRequest);
        } else {
            result = audio.requestAudioFocus(focusListener, AudioManager.STREAM_MUSIC,
                AudioManager.AUDIOFOCUS_GAIN_TRANSIENT);
        }
        return result == AudioManager.AUDIOFOCUS_REQUEST_GRANTED;
    }

    private void releaseFocus() {
        if (noisyRegistered) {
            unregisterReceiver(noisy);
            noisyRegistered = false;
        }
        if (audio == null) return;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            if (focusRequest != null) audio.abandonAudioFocusRequest(focusRequest);
        } else {
            audio.abandonAudioFocus(focusListener);
        }
    }

    @Override
    public void onDestroy() {
        releaseFocus();
        releasePlayer();
        if (tts != null) {
            tts.stop();
            tts.shutdown();
            tts = null;
        }
        running = false;
        WidgetStore.setSpeaking(this, false);
        Widgets.refresh(this, ListenWidget.class);
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void startInForeground() {
        NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            if (manager != null && manager.getNotificationChannel(CHANNEL_ID) == null) {
                NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID, "Listen to your day", NotificationManager.IMPORTANCE_LOW);
                channel.setDescription("Shown while today's brief is read aloud from the widget");
                channel.setSound(null, null);
                manager.createNotificationChannel(channel);
            }
            builder = new Notification.Builder(this, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
        }
        PendingIntent stop = ListenWidget.speech(this, ACTION_STOP);
        Notification notification = builder
            .setSmallIcon(R.drawable.ic_stat_siddha)
            .setContentTitle("Listening to your day")
            .setContentText("Siddha is reading today’s brief")
            .setContentIntent(Widgets.open(this, "/m/today"))
            .setOngoing(true)
            .addAction(new Notification.Action.Builder(null, "Stop", stop).build())
            .build();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK);
        } else {
            startForeground(NOTIFICATION_ID, notification);
        }
    }

    /** TextToSpeech caps one utterance; break at sentence ends under the cap. */
    static List<String> split(String text, int max) {
        List<String> out = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        for (String sentence : text.split("(?<=[.!?])\\s+")) {
            if (current.length() > 0 && current.length() + sentence.length() + 1 > max) {
                out.add(current.toString());
                current.setLength(0);
            }
            if (current.length() > 0) current.append(' ');
            current.append(sentence.length() > max ? sentence.substring(0, max) : sentence);
        }
        if (current.length() > 0) out.add(current.toString());
        return out;
    }
}
