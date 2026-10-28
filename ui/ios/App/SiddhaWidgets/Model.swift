import Foundation

// What the widgets draw from: the parts the app publishes
// (ui/src/app/core/widget-bridge.service.ts), decoded leniently so an older
// app version's part, missing the newer fields, still draws. Foundation only,
// so the views can be rendered on a Mac for review (scripts in
// ui/ios/WidgetPreview/).

struct TimingWindow: Decodable, Hashable {
    var name: String
    var kind: String
    var startMs: Double
    var endMs: Double

    var start: Date { Date(timeIntervalSince1970: startMs / 1000) }
    var end: Date { Date(timeIntervalSince1970: endMs / 1000) }
    var caution: Bool { kind == "inauspicious" }
}

struct TodayPart: Decodable {
    var date: String = ""
    var score: Int = 0
    var band: String = ""
    var label: String = ""
    var headline: String = ""
    var summary: String = ""
    var doItem: String = ""
    var avoidItem: String = ""
    var doItems: [String] = []
    var avoidItems: [String] = []
    var tithi: String = ""
    var nakshatra: String = ""
    var yoga: String = ""
    var moonSign: String = ""
    var masa: String = ""
    var sunriseMs: Double = 0
    var windows: [TimingWindow] = []
    var listen: String = ""

    init() {}

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: Keys.self)
        func text(_ key: Keys) -> String { (try? c.decode(String.self, forKey: key)) ?? "" }
        date = text(.date)
        score = (try? c.decode(Int.self, forKey: .score)) ?? Int((try? c.decode(Double.self, forKey: .score)) ?? 0)
        band = text(.band)
        label = text(.label)
        headline = text(.headline)
        summary = text(.summary)
        doItem = text(.doItem)
        avoidItem = text(.avoidItem)
        doItems = (try? c.decode([String].self, forKey: .doItems)) ?? []
        avoidItems = (try? c.decode([String].self, forKey: .avoidItems)) ?? []
        tithi = text(.tithi)
        nakshatra = text(.nakshatra)
        yoga = text(.yoga)
        moonSign = text(.moonSign)
        masa = text(.masa)
        sunriseMs = (try? c.decode(Double.self, forKey: .sunriseMs)) ?? 0
        windows = (try? c.decode([TimingWindow].self, forKey: .windows)) ?? []
        listen = text(.listen)
    }

    private enum Keys: String, CodingKey {
        case date, score, band, label, headline, summary, doItem, avoidItem, doItems, avoidItems
        case tithi, nakshatra, yoga, moonSign, masa, sunriseMs, windows, listen
    }

    /// Up to two Do and two Avoid lines, without their own "Do"/"Avoid" label.
    var dos: [String] { Self.items(doItems.isEmpty ? [doItem] : doItems, label: "Do") }
    var avoids: [String] { Self.items(avoidItems.isEmpty ? [avoidItem] : avoidItems, label: "Avoid") }

    static func items(_ list: [String], label: String) -> [String] {
        list.map { strip($0, label: label) }.filter { !$0.isEmpty }.prefix(2).map { $0 }
    }

    /// "Avoid overextending yourself" reads "Overextending yourself" in the Avoid row.
    static func strip(_ text: String, label: String) -> String {
        var t = text.trimmingCharacters(in: .whitespaces)
        for prefix in [label + " ", label + ":"] where t.lowercased().hasPrefix(prefix.lowercased()) {
            t = String(t.dropFirst(prefix.count)).trimmingCharacters(in: .whitespaces)
        }
        guard let first = t.first else { return t }
        return first.uppercased() + t.dropFirst()
    }
}

struct DatedName: Decodable, Hashable {
    var date: String
    var name: String
    var approx: Bool?
}

struct MoonDay: Decodable, Hashable {
    var date: String
    var moon: String
    var approx: Bool?
    var full: Bool { moon == "full" }
}

struct CalendarDay: Decodable, Hashable {
    var date: String
    var tithi: String?
    var quality: String?
}

struct CalendarPart: Decodable {
    var festivals: [DatedName] = []
    var vrats: [DatedName] = []
    var moonDays: [MoonDay] = []
    var days: [CalendarDay] = []
    /// The whole of this month, for the large calendar (newer apps only).
    var month: [CalendarDay] = []

    init() {}

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: Keys.self)
        festivals = (try? c.decode([DatedName].self, forKey: .festivals)) ?? []
        vrats = (try? c.decode([DatedName].self, forKey: .vrats)) ?? []
        moonDays = (try? c.decode([MoonDay].self, forKey: .moonDays)) ?? []
        days = (try? c.decode([CalendarDay].self, forKey: .days)) ?? []
        month = (try? c.decode([CalendarDay].self, forKey: .month)) ?? []
    }

    private enum Keys: String, CodingKey { case festivals, vrats, moonDays, days, month }

    func day(_ iso: String) -> CalendarDay? {
        days.first { $0.date == iso } ?? month.first { $0.date == iso }
    }

    /// The next full or new moon from this day.
    func nextMoon(from iso: String) -> MoonDay? {
        moonDays.filter { $0.date >= iso }.min { $0.date < $1.date }
    }
}

struct Verse: Decodable, Hashable {
    var date: String
    var sanskrit: String = ""
    var english: String = ""
    var meaning: String = ""
    var source: String = ""
    var ref: String = ""

    init(date: String, sanskrit: String, english: String, meaning: String, source: String, ref: String) {
        self.date = date; self.sanskrit = sanskrit; self.english = english
        self.meaning = meaning; self.source = source; self.ref = ref
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: Keys.self)
        func text(_ key: Keys) -> String { (try? c.decode(String.self, forKey: key)) ?? "" }
        date = text(.date); sanskrit = text(.sanskrit); english = text(.english)
        meaning = text(.meaning); source = text(.source); ref = text(.ref)
    }

    private enum Keys: String, CodingKey { case date, sanskrit, english, meaning, source, ref }

    /// The verse's first line, without the danda that ends it.
    var firstLine: String {
        let line = sanskrit.trimmingCharacters(in: .whitespacesAndNewlines)
            .components(separatedBy: "\n").first ?? ""
        return line.trimmingCharacters(in: CharacterSet(charactersIn: " ।॥\t"))
    }
}

struct SubhashitaPart: Decodable {
    var days: [Verse] = []

    init(days: [Verse] = []) { self.days = days }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: Keys.self)
        days = (try? c.decode([Verse].self, forKey: .days)) ?? []
    }

    private enum Keys: String, CodingKey { case days }
}

struct MantraPart: Decodable {
    var key: String = ""
    var title: String = ""
    var target: Int = 108
    var count: Int = 0
    var date: String = ""
    var route: String = "/m/remedies"

    init() {}

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: Keys.self)
        key = (try? c.decode(String.self, forKey: .key)) ?? ""
        title = (try? c.decode(String.self, forKey: .title)) ?? ""
        target = max(1, (try? c.decode(Int.self, forKey: .target)) ?? 108)
        count = (try? c.decode(Int.self, forKey: .count)) ?? 0
        date = (try? c.decode(String.self, forKey: .date)) ?? ""
        route = (try? c.decode(String.self, forKey: .route)) ?? "/m/remedies"
    }

    private enum Keys: String, CodingKey { case key, title, target, count, date, route }
}

/// One moment of every part, as a timeline entry carries it.
struct Snapshot {
    var now: Date
    var today: TodayPart?
    var calendar: CalendarPart?
    var subhashita: SubhashitaPart?
    var mantra: MantraPart?
    var opacity: Double = 1

    var iso: String { WidgetGroup.isoDay(now) }

    /// Today's reading, only if it is for this day: widgets show nothing stale.
    var freshToday: TodayPart? {
        guard let today, today.date == iso else { return nil }
        return today
    }

    var verse: Verse? { subhashita?.days.first { $0.date == iso } }

    /// A count from an earlier day is not today's: the practice starts again.
    var mantraCount: Int {
        guard let mantra, mantra.date == iso else { return 0 }
        return mantra.count
    }

    static func load(at now: Date = Date()) -> Snapshot {
        func decode<T: Decodable>(_ part: String, _ type: T.Type) -> T? {
            guard let data = WidgetGroup.data(part) else { return nil }
            return try? JSONDecoder().decode(T.self, from: data)
        }
        return Snapshot(
            now: now,
            today: decode("today", TodayPart.self),
            calendar: decode("calendar", CalendarPart.self),
            subhashita: decode("subhashita", SubhashitaPart.self),
            mantra: decode("mantra", MantraPart.self),
            opacity: Double(WidgetGroup.opacity) / 100
        )
    }
}

// MARK: Timing

extension TodayPart {
    /// The window to show: Rahu Kalam until it ends, then the next one ahead.
    func currentWindow(at now: Date) -> TimingWindow? {
        let open = windows.filter { $0.end > now }
        if let rahu = open.first(where: { $0.name.hasPrefix("Rahu Kalam") }) { return rahu }
        return open.min { $0.start < $1.start }
    }

    /// The next good window that has not ended, after `after` if given.
    func nextGood(at now: Date, after: TimingWindow? = nil) -> TimingWindow? {
        windows.filter { !$0.caution && $0.end > now && (after == nil || $0.start >= after!.start) && $0 != after }
            .min { $0.start < $1.start }
    }

    func nextCaution(at now: Date) -> TimingWindow? {
        windows.filter { $0.caution && $0.end > now }.min { $0.start < $1.start }
    }

    /// The day's span for the timeline: sunrise (or the first window) to the last window's end.
    func daySpan() -> ClosedRange<Date>? {
        guard let first = windows.map(\.start).min(), let last = windows.map(\.end).max() else { return nil }
        let start = sunriseMs > 0 ? min(Date(timeIntervalSince1970: sunriseMs / 1000), first) : first
        return start < last ? start...last : nil
    }
}

enum Say {
    static func duration(_ seconds: TimeInterval) -> String {
        let minutes = max(1, Int((seconds / 60).rounded()))
        if minutes < 60 { return "\(minutes) min" }
        let h = minutes / 60, m = minutes % 60
        return m == 0 ? "\(h)h" : "\(h)h \(m)m"
    }

    /// "Rahu Kalam in 2h 14m" or "Rahu Kalam ends in 38 min".
    static func windowLine(_ w: TimingWindow, at now: Date) -> String {
        now < w.start ? "\(w.name) in \(duration(w.start.timeIntervalSince(now)))"
            : "\(w.name) ends in \(duration(w.end.timeIntervalSince(now)))"
    }

    static func clock(_ date: Date) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_IN")
        f.dateFormat = "h:mm"
        return f.string(from: date)
    }

    static func span(_ w: TimingWindow) -> String { "\(clock(w.start)) – \(clock(w.end))" }

    static func date(_ iso: String, _ format: String) -> String {
        guard let d = parse(iso) else { return iso }
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_GB")
        f.dateFormat = format
        return f.string(from: d)
    }

    static func parse(_ iso: String) -> Date? {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.calendar = Calendar(identifier: .gregorian)
        f.dateFormat = "yyyy-MM-dd"
        return f.date(from: iso)
    }

    /// "today", "tomorrow" or "in 3 days".
    static func daysUntil(from: String, to: String) -> String {
        guard let a = parse(from), let b = parse(to) else { return "" }
        let days = Calendar(identifier: .gregorian).dateComponents([.day], from: a, to: b).day ?? 0
        return days == 0 ? "today" : days == 1 ? "tomorrow" : "in \(days) days"
    }

    /// "Krishna Dwadashi" -> "Dwadashi", for the week strip's narrow cells.
    static func shortTithi(_ tithi: String) -> String {
        var t = tithi
        for prefix in ["Shukla ", "Krishna "] where t.hasPrefix(prefix) { t.removeFirst(prefix.count) }
        return t
    }

    /// About how long the Listen script runs aloud, at an unhurried pace.
    static func listenLength(_ text: String) -> String {
        let words = text.split { $0 == " " || $0 == "\n" }.count
        let minutes = max(1, Int((Double(words) / 140).rounded()))
        return "about \(minutes) min"
    }
}

// MARK: Calendar events

struct DayEvent: Hashable {
    var date: String
    var text: String
    var approx: Bool
}

extension CalendarPart {
    /// Festivals, vrat days and full and new moons, one row a day in date
    /// order (CalendarWidget.weekEvents on Android). A vrat a festival already
    /// names and a moon a vrat already names are not listed twice.
    func events(from: String, to: String) -> [DayEvent] {
        var byDate: [String: (text: String, seen: String, approx: Bool)] = [:]
        for row in festivals + vrats where row.date >= from && row.date <= to && !row.name.isEmpty {
            var entry = byDate[row.date] ?? ("", "", false)
            if covered(entry.seen, row.name) { continue }
            entry.text += entry.text.isEmpty ? row.name : ", \(row.name)"
            entry.seen += " " + row.name.lowercased()
            entry.approx = entry.approx || (row.approx ?? false)
            byDate[row.date] = entry
        }
        for row in moonDays where row.date >= from && row.date <= to {
            var entry = byDate[row.date] ?? ("", "", false)
            let word = row.full ? "purnima" : "amavasya"
            if entry.seen.contains(word) || entry.seen.contains(row.full ? "full moon" : "new moon") { continue }
            entry.text += entry.text.isEmpty ? (row.full ? "Purnima" : "Amavasya") : (row.full ? " · Purnima" : " · Amavasya")
            entry.seen += " " + word
            byDate[row.date] = entry
        }
        return byDate.keys.sorted().map { DayEvent(date: $0, text: byDate[$0]!.text, approx: byDate[$0]!.approx) }
    }

    private func covered(_ seen: String, _ name: String) -> Bool {
        let n = name.lowercased()
        return ["ekadashi", "pradosh", "purnima", "amavasya"].contains { n.contains($0) && seen.contains($0) }
    }

    func marked(from: String, to: String) -> Set<String> {
        Set(events(from: from, to: to).map(\.date))
    }
}

enum Days {
    /// `count` YYYY-MM-DD days from `iso`.
    static func from(_ iso: String, count: Int) -> [String] {
        guard let start = Say.parse(iso) else { return [] }
        let cal = Calendar(identifier: .gregorian)
        return (0..<count).compactMap { cal.date(byAdding: .day, value: $0, to: start) }.map(WidgetGroup.isoDay)
    }

    /// The month of `iso` as weeks of optional day numbers, Sunday first.
    static func month(of iso: String) -> (title: String, weeks: [[String?]]) {
        guard let date = Say.parse(iso) else { return ("", []) }
        let cal = Calendar(identifier: .gregorian)
        let comps = cal.dateComponents([.year, .month], from: date)
        guard let first = cal.date(from: comps), let range = cal.range(of: .day, in: .month, for: first) else { return ("", []) }
        let lead = cal.component(.weekday, from: first) - 1
        var cells: [String?] = Array(repeating: nil, count: lead)
        cells += range.map { String(format: "%04d-%02d-%02d", comps.year ?? 0, comps.month ?? 0, $0) }
        while cells.count % 7 != 0 { cells.append(nil) }
        let weeks = stride(from: 0, to: cells.count, by: 7).map { Array(cells[$0..<$0 + 7]) }
        return (Say.date(iso, "MMMM yyyy"), weeks)
    }
}
