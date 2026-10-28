import AppIntents
import SwiftUI
import WidgetKit

// The WidgetKit side: one timeline for every widget, the widgets and their
// sizes, the lock-screen shapes, the mantra tap and the Ask control. The
// faces themselves are in Views.swift.

// MARK: Timeline

struct SiddhaEntry: TimelineEntry {
    let date: Date
    let snap: Snapshot
}

struct SiddhaProvider: TimelineProvider {
    func placeholder(in context: Context) -> SiddhaEntry {
        SiddhaEntry(date: Date(), snap: Sample.snapshot(at: Date()))
    }

    /// The gallery shows the reader's own day when the app has published
    /// one, and the illustrative day before that.
    func getSnapshot(in context: Context, completion: @escaping (SiddhaEntry) -> Void) {
        let now = Date()
        let snap = Snapshot.load(at: now)
        let show = context.isPreview && snap.freshToday == nil ? Sample.snapshot(at: now) : snap
        completion(SiddhaEntry(date: now, snap: show))
    }

    /// An entry every five minutes until midnight, plus one at every
    /// window's start and end, so the "in 2h 14m" lines stay true without
    /// the app; at midnight the day turns over and the timeline reloads.
    /// The app reloads it whenever it publishes.
    func getTimeline(in context: Context, completion: @escaping (Timeline<SiddhaEntry>) -> Void) {
        let now = Date()
        let base = Snapshot.load(at: now)
        let cal = Calendar.current
        let midnight = cal.date(byAdding: .day, value: 1, to: cal.startOfDay(for: now)) ?? now.addingTimeInterval(86_400)

        var times = Set<Date>([now])
        var t = now
        while t < midnight {
            t = t.addingTimeInterval(300)
            if t < midnight { times.insert(t) }
        }
        for w in base.freshToday?.windows ?? [] {
            for edge in [w.start, w.end] where edge > now && edge < midnight { times.insert(edge) }
        }
        times.insert(midnight.addingTimeInterval(1))

        let entries = times.sorted().map { time -> SiddhaEntry in
            var snap = base
            snap.now = time
            return SiddhaEntry(date: time, snap: snap)
        }
        completion(Timeline(entries: entries, policy: .atEnd))
    }
}

// MARK: The card

struct Card<Content: View>: View {
    @Environment(\.colorScheme) private var scheme
    var snap: Snapshot
    var route: String
    @ViewBuilder var content: (Palette) -> Content

    var body: some View {
        let palette = Palette.of(scheme)
        content(palette)
            .widgetURL(WidgetGroup.url(route))
            .containerBackground(for: .widget) {
                GlassCard(palette: palette, opacity: snap.opacity)
            }
    }
}

/// Lock screen shapes: Apple tints them, so they are drawn in one colour.
struct Accessory<Content: View>: View {
    var route: String
    @ViewBuilder var content: () -> Content

    var body: some View {
        content()
            .widgetURL(WidgetGroup.url(route))
            .containerBackground(for: .widget) { Color.clear }
    }
}

extension WidgetFamily {
    var size: Size {
        switch self {
        case .systemSmall: return .small
        case .systemMedium: return .medium
        case .systemExtraLarge: return .extraLarge
        default: return .large
        }
    }
}

// MARK: Your day

struct TodayWidgetView: View {
    @Environment(\.widgetFamily) private var family
    var entry: SiddhaEntry

    var body: some View {
        let snap = entry.snap
        let today = snap.freshToday
        switch family {
        case .accessoryCircular:
            Accessory(route: "/m/today") {
                ZStack {
                    AccessoryWidgetBackground()
                    Ring(progress: Double(today?.score ?? 0) / 100, color: Color.primary, track: Color.primary.opacity(0.25), width: 4.5)
                        .padding(3)
                    VStack(spacing: 0) {
                        Text(today.map { "\($0.score)" } ?? "–").font(.system(size: 18, weight: .bold)).monospacedDigit()
                        if let label = today?.label, !label.isEmpty {
                            Text(label.uppercased()).font(.system(size: 6.5, weight: .semibold)).lineLimit(1).minimumScaleFactor(0.6)
                        }
                    }
                }
                .widgetAccentable()
            }
        case .accessoryInline:
            Accessory(route: "/m/today") {
                ViewThatFits {
                    Text(inline(snap, long: true))
                    Text(inline(snap, long: false))
                }
            }
        case .accessoryRectangular:
            Accessory(route: "/m/today") {
                VStack(alignment: .leading, spacing: 1) {
                    Text(today.map { "\($0.score) · \($0.label)".uppercased() } ?? "YOUR DAY")
                        .font(.system(size: 11, weight: .bold)).widgetAccentable()
                    Text(today?.headline ?? "Open Siddha to see your day")
                        .font(.system(size: 13, weight: .semibold)).lineLimit(2)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        default:
            Card(snap: snap, route: "/m/today") { palette in
                TodayFace(snap: snap, palette: palette, size: family.size)
            }
        }
    }

    /// The line above the lock-screen clock: the tithi, and a festival on festival days.
    private func inline(_ snap: Snapshot, long: Bool) -> String {
        let tithi = snap.freshToday?.tithi ?? snap.calendar?.day(snap.iso)?.tithi ?? ""
        let festival = snap.calendar?.events(from: snap.iso, to: snap.iso).first?.text
        if let festival { return long && !tithi.isEmpty ? "\(festival) · \(tithi)" : festival }
        if long, let today = snap.freshToday, !today.nakshatra.isEmpty { return "\(tithi) · \(today.nakshatra)" }
        return tithi.isEmpty ? "Siddha" : tithi
    }
}

struct TodayWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "today", provider: SiddhaProvider()) { entry in
            TodayWidgetView(entry: entry)
        }
        .configurationDisplayName("Your day")
        .description("Today’s score, headline, panchang and timings.")
        .supportedFamilies([.systemSmall, .systemMedium, .systemLarge,
                            .accessoryCircular, .accessoryRectangular, .accessoryInline])
    }
}

// MARK: Calendar

struct CalendarWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "calendar", provider: SiddhaProvider()) { entry in
            CalendarWidgetView(entry: entry)
        }
        .configurationDisplayName("Calendar")
        .description("Your week or month: good days, take-care days and festivals.")
        .supportedFamilies([.systemSmall, .systemMedium, .systemLarge, .systemExtraLarge])
    }
}

struct CalendarWidgetView: View {
    @Environment(\.widgetFamily) private var family
    var entry: SiddhaEntry

    var body: some View {
        Card(snap: entry.snap, route: "/m/calendar") { palette in
            CalendarFace(snap: entry.snap, palette: palette, size: family.size)
        }
    }
}

// MARK: Timing

struct TimingWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "timing", provider: SiddhaProvider()) { entry in
            TimingWidgetView(entry: entry)
        }
        .configurationDisplayName("Rahu Kalam")
        .description("Rahu Kalam and today’s windows, counting down.")
        .supportedFamilies([.systemSmall, .accessoryRectangular])
    }
}

struct TimingWidgetView: View {
    @Environment(\.widgetFamily) private var family
    var entry: SiddhaEntry

    var body: some View {
        let snap = entry.snap
        if family == .accessoryRectangular {
            Accessory(route: "/m/today") {
                let window = snap.freshToday?.currentWindow(at: snap.now)
                VStack(alignment: .leading, spacing: 1) {
                    Text((window?.name ?? "Today’s windows").uppercased())
                        .font(.system(size: 11, weight: .bold))
                        .widgetAccentable()
                    if let window {
                        let running = snap.now >= window.start
                        HStack(spacing: 4) {
                            Text(running ? "ends in" : "in").font(.system(size: 13, weight: .medium))
                            Text(timerInterval: snap.now...(running ? window.end : window.start), countsDown: true)
                                .font(.system(size: 16, weight: .semibold))
                                .monospacedDigit()
                        }
                        Text(Say.span(window)).font(.system(size: 11)).foregroundStyle(.secondary)
                    } else {
                        Text(snap.freshToday == nil ? "Open Siddha" : "All done for today").font(.system(size: 13))
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        } else {
            Card(snap: snap, route: "/m/today") { palette in
                TimingFace(snap: snap, palette: palette)
            }
        }
    }
}

// MARK: Moon

struct MoonWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "moon", provider: SiddhaProvider()) { entry in
            MoonWidgetView(entry: entry)
        }
        .configurationDisplayName("Moon")
        .description("The moon today and the next Purnima or Amavasya.")
        .supportedFamilies([.systemSmall, .accessoryCircular])
    }
}

struct MoonWidgetView: View {
    @Environment(\.widgetFamily) private var family
    var entry: SiddhaEntry

    var body: some View {
        if family == .accessoryCircular {
            Accessory(route: "/m/calendar") {
                ZStack {
                    AccessoryWidgetBackground()
                    ZStack {
                        Circle().fill(Color.primary.opacity(0.22))
                        MoonShape(phase: MoonShape.phase(at: entry.snap.now)).fill(Color.primary)
                    }
                    .padding(9)
                }
                .widgetAccentable()
            }
        } else {
            Card(snap: entry.snap, route: "/m/calendar") { palette in
                MoonFace(snap: entry.snap, palette: palette)
            }
        }
    }
}

// MARK: Mantra

/// One count on the widget's ring. The widget keeps it and hands it to the
/// app the next time it opens (SiddhaWidgetsPlugin.takeMantraTaps), so the
/// home screen and the app keep one count.
struct CountMantraIntent: AppIntent {
    static var title: LocalizedStringResource = "Count one"
    static var description = IntentDescription("Adds one to today’s mantra count.")
    static var isDiscoverable: Bool = false

    func perform() async throws -> some IntentResult {
        guard let raw = WidgetGroup.object("mantra") else { return .result() }
        var mantra = raw
        let today = WidgetGroup.isoDay()
        let target = max(1, mantra["target"] as? Int ?? 108)
        let count = (mantra["date"] as? String) == today ? (mantra["count"] as? Int ?? 0) : 0
        guard count < target else { return .result() }
        mantra["count"] = count + 1
        mantra["date"] = today
        if let data = try? JSONSerialization.data(withJSONObject: mantra), let json = String(data: data, encoding: .utf8) {
            WidgetGroup.put("mantra", json: json)
            WidgetGroup.addMantraTap(key: mantra["key"] as? String ?? "", date: today)
        }
        return .result()
    }
}

struct MantraWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "mantra", provider: SiddhaProvider()) { entry in
            MantraWidgetView(entry: entry)
        }
        .configurationDisplayName("Mantra")
        .description("Count your mantra with a tap.")
        .supportedFamilies([.systemSmall, .accessoryCircular])
    }
}

struct MantraWidgetView: View {
    @Environment(\.widgetFamily) private var family
    var entry: SiddhaEntry

    var body: some View {
        let snap = entry.snap
        let route = snap.mantra?.route ?? "/m/remedies"
        if family == .accessoryCircular {
            Accessory(route: route) {
                Button(intent: CountMantraIntent()) {
                    ZStack {
                        AccessoryWidgetBackground()
                        Ring(progress: Double(snap.mantraCount) / Double(snap.mantra?.target ?? 108),
                             color: Color.primary, track: Color.primary.opacity(0.25), width: 4.5)
                            .padding(3)
                        Text("\(snap.mantraCount)").font(.system(size: 17, weight: .bold)).monospacedDigit()
                    }
                }
                .buttonStyle(.plain)
                .widgetAccentable()
            }
        } else {
            Card(snap: snap, route: route) { palette in
                MantraFace(snap: snap, palette: palette) { ring in
                    Button(intent: CountMantraIntent()) { ring }
                        .buttonStyle(.plain)
                        .disabled(snap.mantra == nil || snap.mantraCount >= (snap.mantra?.target ?? 108))
                }
            }
        }
    }
}

// MARK: Listen, Ask, Subhashita

struct ListenWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "listen", provider: SiddhaProvider()) { entry in
            Card(snap: entry.snap, route: "/m/today?listen=1") { palette in
                ListenFace(snap: entry.snap, palette: palette)
            }
        }
        .configurationDisplayName("Listen")
        .description("Hear today’s reading in Siddha’s voice.")
        .supportedFamilies([.systemSmall])
    }
}

struct AskWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "ask", provider: SiddhaProvider()) { entry in
            AskWidgetView(entry: entry)
        }
        .configurationDisplayName("Ask Siddha")
        .description("Ask a question from the home screen.")
        .supportedFamilies([.systemSmall, .accessoryCircular])
    }
}

struct AskWidgetView: View {
    @Environment(\.widgetFamily) private var family
    var entry: SiddhaEntry

    var body: some View {
        if family == .accessoryCircular {
            Accessory(route: "/m/ask") {
                ZStack {
                    AccessoryWidgetBackground()
                    VStack(spacing: 1) {
                        Image(systemName: "sparkles").font(.system(size: 17, weight: .semibold))
                        Text("ASK").font(.system(size: 8, weight: .bold))
                    }
                }
                .widgetAccentable()
            }
        } else {
            Card(snap: entry.snap, route: "/m/ask") { palette in
                AskFace(palette: palette)
            }
        }
    }
}

struct SubhashitaWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "subhashita", provider: SiddhaProvider()) { entry in
            SubhashitaWidgetView(entry: entry)
        }
        .configurationDisplayName("Today’s Subhashita")
        .description("A verse a day from the Gita, Chanakya Niti and the Puranas.")
        .supportedFamilies([.systemMedium, .systemLarge])
    }
}

struct SubhashitaWidgetView: View {
    @Environment(\.widgetFamily) private var family
    var entry: SiddhaEntry

    var body: some View {
        Card(snap: entry.snap, route: "/m/subhashita") { palette in
            SubhashitaFace(snap: entry.snap, palette: palette, size: family.size)
        }
    }
}

// MARK: Control Centre (iOS 18)

@available(iOS 18.0, *)
struct OpenAskIntent: AppIntent {
    static var title: LocalizedStringResource = "Ask Siddha"
    static var isDiscoverable: Bool = false

    func perform() async throws -> some IntentResult & OpensIntent {
        .result(opensIntent: OpenURLIntent(WidgetGroup.url("/m/ask")))
    }
}

@available(iOS 18.0, *)
struct AskControl: ControlWidget {
    var body: some ControlWidgetConfiguration {
        StaticControlConfiguration(kind: "app.asksiddha.mobile.ask") {
            ControlWidgetButton(action: OpenAskIntent()) {
                Label("Ask Siddha", systemImage: "sparkles")
            }
        }
        .displayName("Ask Siddha")
        .description("Open Ask from Control Centre or the lock screen.")
    }
}

// MARK: Bundle

@main
struct SiddhaWidgetBundle: WidgetBundle {
    init() {
        Fonts.register()
    }

    var body: some Widget {
        TodayWidget()
        CalendarWidget()
        TimingWidget()
        MoonWidget()
        MantraWidget()
        SubhashitaWidget()
        ListenWidget()
        AskWidget()
        if #available(iOS 18.0, *) {
            AskControl()
        }
    }
}
