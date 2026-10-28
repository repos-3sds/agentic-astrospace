import Foundation

/// An illustrative day: what the widget gallery shows before the app has
/// published anything, and what ui/ios/WidgetPreview renders for review.
/// Never shown in place of a real reading once one exists.
enum Sample {
    static func snapshot(at now: Date, iso override: String? = nil) -> Snapshot {
        let iso = override ?? WidgetGroup.isoDay(now)
        let cal = Calendar.current
        let midnight = Say.parse(iso).map { cal.startOfDay(for: $0) } ?? cal.startOfDay(for: now)
        func at(_ h: Int, _ m: Int) -> Double { (midnight.timeIntervalSince1970 + Double(h * 3600 + m * 60)) * 1000 }
        let week = Days.from(iso, count: 40)

        var today = TodayPart()
        today.date = iso
        today.score = 58
        today.band = "steady"
        today.label = "Steady"
        today.headline = "A good day to finish what you started"
        today.summary = "Steady work goes well. Small talks with family settle easily; leave big money calls for tomorrow."
        today.doItems = ["Finish one task before noon", "Call someone you have been meaning to"]
        today.avoidItems = ["Lending money today", "Starting a new purchase"]
        today.tithi = "Krishna Dwadashi"
        today.nakshatra = "Uttara Phalguni"
        today.yoga = "Siddhi"
        today.moonSign = "Kanya"
        today.masa = "Kartika · Krishna paksha"
        today.sunriseMs = at(6, 12)
        today.windows = [
            TimingWindow(name: "Rahu Kalam", kind: "inauspicious", startMs: at(9, 15), endMs: at(10, 40)),
            TimingWindow(name: "Abhijit", kind: "auspicious", startMs: at(11, 37), endMs: at(12, 23)),
            TimingWindow(name: "Yamaganda", kind: "inauspicious", startMs: at(13, 30), endMs: at(15, 0)),
            TimingWindow(name: "Amrit Kalam", kind: "auspicious", startMs: at(15, 10), endMs: at(16, 45)),
        ]
        today.listen = String(repeating: "word ", count: 150)

        let tithis = ["Krishna Dwadashi", "Krishna Trayodashi", "Krishna Chaturdashi", "Amavasya",
                      "Shukla Pratipada", "Shukla Dwitiya", "Shukla Tritiya"]
        let qualities = ["good", "", "care", "good", "good", "care", ""]
        var calendar = CalendarPart()
        calendar.days = (0..<7).map { CalendarDay(date: week[$0], tithi: tithis[$0], quality: qualities[$0]) }
        let monthQuality = ["good", "", "care", "", "good", "", "good", "care", "", "", "good", "care", ""]
        calendar.month = Days.month(of: iso).weeks.flatMap { $0 }.compactMap { $0 }.enumerated().map {
            CalendarDay(date: $0.element, tithi: nil, quality: monthQuality[$0.offset % monthQuality.count])
        }
        calendar.festivals = [
            DatedName(date: week[2], name: "Naraka Chaturdashi", approx: nil),
            DatedName(date: week[3], name: "Diwali", approx: nil),
            DatedName(date: week[4], name: "Govardhan Puja", approx: nil),
            DatedName(date: week[5], name: "Bhai Dooj", approx: nil),
        ]
        calendar.moonDays = [MoonDay(date: week[3], moon: "new", approx: true), MoonDay(date: week[18], moon: "full", approx: true)]

        let verse = Verse(
            date: iso,
            sanskrit: "मात्रास्पर्शास्तु कौन्तेय शीतोष्णसुखदुःखदाः ।\nआगमापायिनोऽनित्यास्तांस्तितिक्षस्व भारत ॥",
            english: "Heat and cold, joy and pain come and go; bear them calmly.",
            meaning: "Good times and hard times both pass. Stay patient through them.",
            source: "Bhagavad Gita", ref: "2.14")

        var mantra = MantraPart()
        mantra.key = "sample"
        mantra.title = "Om Namah Shivaya"
        mantra.target = 108
        mantra.count = 43
        mantra.date = iso

        return Snapshot(now: now, today: today, calendar: calendar, subhashita: SubhashitaPart(days: [verse]),
                        mantra: mantra, opacity: 1)
    }
}
