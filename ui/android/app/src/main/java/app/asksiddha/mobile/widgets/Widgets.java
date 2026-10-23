package app.asksiddha.mobile.widgets;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.res.Configuration;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.net.Uri;
import android.os.Build;
import android.util.SparseArray;
import android.util.TypedValue;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.RemoteViews;
import android.widget.TextView;
import app.asksiddha.mobile.MainActivity;
import app.asksiddha.mobile.R;
import java.util.Calendar;
import java.util.Locale;
import org.json.JSONArray;
import org.json.JSONObject;

/** Shared plumbing for the widgets: refresh, taps into the app, and drawing. */
public final class Widgets {

    public static final String EXTRA_ROUTE = "siddha_route";
    static final String ACTION_REFRESH = "app.asksiddha.mobile.widgets.REFRESH";
    static final String ACTION_TICK = "app.asksiddha.mobile.widgets.TICK";

    @SuppressWarnings("unchecked")
    static final Class<? extends BaseWidget>[] ALL = new Class[] {
        TodayWidget.class, ListenWidget.class, CalendarWidget.class, TimingWidget.class,
        MoonWidget.class, MantraWidget.class, AskWidget.class, SubhashitaWidget.class,
    };

    private Widgets() {}

    /** Redraws every Siddha widget on the home screen. */
    public static void refreshAll(Context context) {
        AppWidgetManager manager = AppWidgetManager.getInstance(context);
        for (Class<? extends BaseWidget> type : ALL) refresh(context, manager, type);
        scheduleNextRefresh(context);
        scheduleTick(context);
    }

    /** The minute tick: only the widgets that count down. */
    static void tick(Context context) {
        AppWidgetManager manager = AppWidgetManager.getInstance(context);
        refresh(context, manager, TimingWidget.class);
        refresh(context, manager, TodayWidget.class);
        scheduleTick(context);
    }

    /**
     * Redraws the countdowns at the next minute while a window is still ahead
     * or running and a widget shows one. Not a wakeup alarm: a phone asleep
     * catches up when its screen comes on, which is when anyone looks.
     */
    static void scheduleTick(Context context) {
        AlarmManager alarms = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarms == null) return;
        Intent intent = new Intent(context, WidgetRefreshReceiver.class).setAction(ACTION_TICK);
        PendingIntent pending = PendingIntent.getBroadcast(
            context, 1, intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        long now = System.currentTimeMillis();
        JSONObject today = WidgetStore.get(context, "today");
        boolean counting = today != null && WidgetStore.today().equals(today.optString("date"))
            && TimingWidget.current(today, now) != null
            && (has(context, TimingWidget.class) || has(context, TodayWidget.class));
        if (!counting) {
            alarms.cancel(pending);
            return;
        }
        long next = (now / 60_000L + 1) * 60_000L;
        alarms.setWindow(AlarmManager.RTC, next, 10_000L, pending);
    }

    private static boolean has(Context context, Class<? extends BaseWidget> type) {
        int[] ids = AppWidgetManager.getInstance(context).getAppWidgetIds(new ComponentName(context, type));
        return ids != null && ids.length > 0;
    }

    static void refresh(Context context, Class<? extends BaseWidget> type) {
        refresh(context, AppWidgetManager.getInstance(context), type);
    }

    private static void refresh(Context context, AppWidgetManager manager, Class<? extends BaseWidget> type) {
        int[] ids = manager.getAppWidgetIds(new ComponentName(context, type));
        if (ids == null || ids.length == 0) return;
        BaseWidget widget;
        try {
            widget = type.getDeclaredConstructor().newInstance();
        } catch (ReflectiveOperationException e) {
            return;
        }
        for (int id : ids) widget.draw(context, manager, id);
    }

    /**
     * Fades the card behind a widget to the reader's setting, as Samsung's own
     * widgets do. Every top-level widget layout puts its card in an ImageView
     * with id widget_bg under the content, so only the card fades and the text
     * stays at full strength.
     */
    static RemoteViews applyOpacity(Context context, RemoteViews views) {
        views.setInt(R.id.widget_bg, "setImageAlpha", Math.round(255f * WidgetStore.opacity(context) / 100f));
        return views;
    }

    /**
     * The smallest font scale widget text is drawn at. Below the phone's
     * normal size (Samsung goes down to about 80%) a widget's 10sp eyebrows
     * and day labels become hard to read, and the card does not grow any
     * room from the smaller text, so they stay at their designed size.
     */
    static final float MIN_TEXT_SCALE = 1.0f;

    /**
     * Widget text is in sp, so it follows the phone's font size, which goes
     * to 200% on Android 14 and past that on Samsung, and down to about 80%.
     * A widget is a fixed cell: at the large sizes titles clip and the timing
     * line falls off the bottom; at the small ones the eyebrows are unreadable.
     * So widget text follows the phone only between MIN_TEXT_SCALE (100%) and
     * the app's own cap (MainActivity.MAX_TEXT_ZOOM, 115%) (Hawk, 2026-10-21).
     * Outside that range each text is set to the size it has at the nearer
     * limit, measured by inflating the same layout at that font scale, so
     * Android 14's non-linear scaling is kept. Only text views with an id can
     * be reached; every widget text has one.
     */
    static RemoteViews capText(Context context, RemoteViews views) {
        Configuration config = context.getResources().getConfiguration();
        float cap = MainActivity.MAX_TEXT_ZOOM / 100f;
        float scale = Math.max(MIN_TEXT_SCALE, Math.min(cap, config.fontScale));
        if (scale == config.fontScale) return views;
        SparseArray<Float> sizes = cappedSizes(context, config, scale, views.getLayoutId());
        for (int i = 0; i < sizes.size(); i++) {
            views.setTextViewTextSize(sizes.keyAt(i), TypedValue.COMPLEX_UNIT_PX, sizes.valueAt(i));
        }
        return views;
    }

    private static final SparseArray<SparseArray<Float>> cappedSizes = new SparseArray<>();
    private static float cappedFor = 0f;

    /** Text sizes in px, by view id, for a layout drawn at the clamped font scale. */
    private static synchronized SparseArray<Float> cappedSizes(
            Context context, Configuration config, float scale, int layout) {
        if (cappedFor != config.fontScale) {
            cappedSizes.clear();
            cappedFor = config.fontScale;
        }
        SparseArray<Float> sizes = cappedSizes.get(layout);
        if (sizes != null) return sizes;
        Configuration capped = new Configuration(config);
        capped.fontScale = scale;
        Context at = context.createConfigurationContext(capped);
        sizes = new SparseArray<>();
        collectTextSizes(LayoutInflater.from(at).inflate(layout, null), sizes);
        cappedSizes.put(layout, sizes);
        return sizes;
    }

    private static void collectTextSizes(View view, SparseArray<Float> sizes) {
        if (view instanceof TextView && view.getId() != View.NO_ID) {
            sizes.put(view.getId(), ((TextView) view).getTextSize());
        }
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) collectTextSizes(group.getChildAt(i), sizes);
        }
    }

    /**
     * Wakes the widgets at the next moment their text changes: the next
     * timing window's start or end, else local midnight. Inexact on purpose,
     * which needs no special alarm permission; the system's own 30-minute
     * update (updatePeriodMillis) is the backstop.
     */
    static void scheduleNextRefresh(Context context) {
        AlarmManager alarms = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarms == null) return;
        long now = System.currentTimeMillis();
        long next = nextMidnight(now);
        JSONObject today = WidgetStore.get(context, "today");
        JSONArray windows = today == null ? null : today.optJSONArray("windows");
        if (windows != null) {
            for (int i = 0; i < windows.length(); i++) {
                JSONObject w = windows.optJSONObject(i);
                if (w == null) continue;
                long start = w.optLong("startMs"), end = w.optLong("endMs");
                if (start > now && start < next) next = start;
                if (end > now && end < next) next = end;
            }
        }
        Intent intent = new Intent(context, WidgetRefreshReceiver.class).setAction(ACTION_REFRESH);
        PendingIntent pending = PendingIntent.getBroadcast(
            context, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        alarms.set(AlarmManager.RTC, next + 1000, pending);
    }

    static long nextMidnight(long now) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(now);
        c.add(Calendar.DAY_OF_YEAR, 1);
        c.set(Calendar.HOUR_OF_DAY, 0);
        c.set(Calendar.MINUTE, 0);
        c.set(Calendar.SECOND, 5);
        c.set(Calendar.MILLISECOND, 0);
        return c.getTimeInMillis();
    }

    /** Opens the app on a screen (a /m/... path). One PendingIntent per path. */
    static PendingIntent open(Context context, String route) {
        Intent intent = new Intent(context, MainActivity.class)
            .setAction(Intent.ACTION_VIEW)
            // The data only keeps PendingIntents for different routes apart.
            .setData(Uri.parse("siddha-widget://open" + route))
            .putExtra(EXTRA_ROUTE, route)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        return PendingIntent.getActivity(
            context, route.hashCode(), intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    static PendingIntent broadcast(Context context, Class<?> receiver, String action) {
        Intent intent = new Intent(context, receiver).setAction(action);
        return PendingIntent.getBroadcast(
            context, action.hashCode(), intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    static boolean night(Context context) {
        int mode = context.getResources().getConfiguration().uiMode & android.content.res.Configuration.UI_MODE_NIGHT_MASK;
        return mode == android.content.res.Configuration.UI_MODE_NIGHT_YES;
    }

    static int color(Context context, int id) {
        return Build.VERSION.SDK_INT >= 23 ? context.getColor(id) : context.getResources().getColor(id);
    }

    static float density(Context context) {
        return context.getResources().getDisplayMetrics().density;
    }

    /** The day-quality ring (Figma 103:92): a track and an arc for the score. */
    static Bitmap ring(Context context, int score, int arcColor, int trackColor, int sizeDp, int strokeDp) {
        float d = density(context);
        int size = Math.round(sizeDp * d);
        float stroke = strokeDp * d;
        Bitmap bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bitmap);
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(stroke);
        RectF box = new RectF(stroke / 2, stroke / 2, size - stroke / 2, size - stroke / 2);
        paint.setColor(trackColor);
        canvas.drawArc(box, 0, 360, false, paint);
        paint.setColor(arcColor);
        paint.setStrokeCap(Paint.Cap.ROUND);
        float sweep = Math.max(0, Math.min(100, score)) * 3.6f;
        canvas.drawArc(box, -90, sweep, false, paint);
        return bitmap;
    }

    /**
     * The moon's shape for a day, lit fraction drawn from the mean synodic
     * month. A picture only: the words beside it (tithi, next full moon) come
     * from the app's panchanga, never from this approximation.
     */
    static Bitmap moon(Context context, long whenMs, int sizeDp) {
        float d = density(context);
        int size = Math.round(sizeDp * d);
        Bitmap bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bitmap);
        float r = size / 2f * 0.92f, cx = size / 2f, cy = size / 2f;
        Paint dark = new Paint(Paint.ANTI_ALIAS_FLAG);
        dark.setColor(color(context, app.asksiddha.mobile.R.color.widget_moon_dark));
        canvas.drawCircle(cx, cy, r, dark);

        // 2000-01-06 18:14 UTC was a new moon; 29.530589 days per lunation.
        double age = ((whenMs - 947182440000L) / 86400000.0) % 29.530589;
        if (age < 0) age += 29.530589;
        double phase = age / 29.530589;                 // 0 new, 0.5 full
        double lit = (1 - Math.cos(2 * Math.PI * phase)) / 2;
        boolean waxing = phase < 0.5;

        Paint light = new Paint(Paint.ANTI_ALIAS_FLAG);
        light.setColor(color(context, app.asksiddha.mobile.R.color.widget_moon_lit));
        Path path = new Path();
        RectF disc = new RectF(cx - r, cy - r, cx + r, cy + r);
        // The lit limb is a half disc; the terminator is a half ellipse whose
        // width runs from r (new or full) through 0 (half).
        path.arcTo(disc, waxing ? -90 : 90, 180, true);
        float w = (float) (r * Math.abs(1 - 2 * lit));
        RectF term = new RectF(cx - w, cy - r, cx + w, cy + r);
        boolean bulges = lit > 0.5;
        path.arcTo(term, waxing ? 90 : -90, bulges ? 180 : -180, false);
        path.close();
        canvas.drawPath(path, light);
        return bitmap;
    }

    /** "in 3 days", "tomorrow", "today" from two YYYY-MM-DD dates. */
    static String daysUntil(String fromIso, String toIso) {
        long days = dayNumber(toIso) - dayNumber(fromIso);
        if (days == 0) return "today";
        if (days == 1) return "tomorrow";
        return String.format(Locale.US, "in %d days", days);
    }

    static long dayNumber(String iso) {
        try {
            String[] p = iso.split("-");
            Calendar c = Calendar.getInstance(java.util.TimeZone.getTimeZone("UTC"));
            c.clear();
            c.set(Integer.parseInt(p[0]), Integer.parseInt(p[1]) - 1, Integer.parseInt(p[2]));
            return c.getTimeInMillis() / 86400000L;
        } catch (RuntimeException e) {
            return 0;
        }
    }

    /** "10:24" in the phone's own clock style. */
    static String clock(long ms) {
        return new java.text.SimpleDateFormat("HH:mm", Locale.ENGLISH).format(new java.util.Date(ms));
    }

    /** "Sat 25 Oct" from a YYYY-MM-DD date. */
    static String shortDate(String iso) {
        try {
            java.text.SimpleDateFormat in = new java.text.SimpleDateFormat("yyyy-MM-dd", Locale.US);
            return new java.text.SimpleDateFormat("EEE d MMM", Locale.ENGLISH).format(in.parse(iso));
        } catch (java.text.ParseException e) {
            return iso;
        }
    }

    /** "Wednesday, 21 October" from a YYYY-MM-DD date, as the Subhashita card dates a verse. */
    static String longDate(String iso) {
        try {
            java.text.SimpleDateFormat in = new java.text.SimpleDateFormat("yyyy-MM-dd", Locale.US);
            return new java.text.SimpleDateFormat("EEEE, d MMMM", Locale.ENGLISH).format(in.parse(iso));
        } catch (java.text.ParseException e) {
            return "";
        }
    }

    /** "1h 20m" or "38 min", for the timing lines that are not live clocks. */
    static String duration(long ms) {
        long minutes = Math.max(1, Math.round(ms / 60000.0));
        if (minutes < 60) return minutes + " min";
        long h = minutes / 60, m = minutes % 60;
        return m == 0 ? h + "h" : h + "h " + m + "m";
    }
}
