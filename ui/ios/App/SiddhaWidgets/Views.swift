import SwiftUI

// The widgets' faces, one view per widget and size. SwiftUI only (no
// WidgetKit), so ui/ios/WidgetPreview can render every size on a Mac for
// review; the WidgetKit wiring is in Widgets.swift. Each face fills its card:
// fixed gaps between the parts and flexible ones that share out what is left,
// so no size ends with an empty band.

enum Size {
    case small, medium, large, extraLarge
}

// MARK: Your day

struct TodayFace: View {
    var snap: Snapshot
    var palette: Palette
    var size: Size

    var body: some View {
        switch size {
        case .small: small
        case .medium: medium
        case .large, .extraLarge: large
        }
    }

    private var today: TodayPart? { snap.freshToday }
    private var dateLabel: String { "Your day · " + Say.date(snap.iso, "EEE d MMM") }

    private var nextLine: String {
        guard let today, let w = today.currentWindow(at: snap.now) else { return "" }
        return Say.windowLine(w, at: snap.now)
    }

    private func score(_ size: CGFloat) -> ScoreRing {
        ScoreRing(palette: palette, score: today?.score, label: today?.label ?? "", band: today?.band ?? "", size: size)
    }

    private var small: some View {
        VStack(spacing: 0) {
            score(76)
            Spacer(minLength: 6)
            Text(today?.tithi.isEmpty == false ? today!.tithi : "Open Siddha")
                .font(Fonts.sans(12, .semibold))
                .foregroundStyle(palette.text)
                .lineLimit(1)
                .minimumScaleFactor(0.8)
            Spacer(minLength: 4)
            if !nextLine.isEmpty {
                TimingLine(palette: palette, text: nextLine, size: 10.5)
                    .minimumScaleFactor(0.75)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var panchangLine: String {
        guard let today else { return "" }
        return [today.tithi, today.nakshatra].filter { !$0.isEmpty }.joined(separator: " · ")
    }

    private var chips: some View {
        let caution = today?.nextCaution(at: snap.now)
        let good = today?.nextGood(at: snap.now)
        return ViewThatFits(in: .horizontal) {
            HStack(spacing: 6) {
                if let caution { cautionChip(caution, long: true) }
                if let good { goodChip(good) }
            }
            HStack(spacing: 6) {
                if let caution { cautionChip(caution, long: false) }
                if let good { goodChip(good) }
            }
            HStack(spacing: 6) {
                if let caution { cautionChip(caution, long: false) } else if let good { goodChip(good) }
            }
        }
    }

    private func cautionChip(_ w: TimingWindow, long: Bool) -> Chip {
        let when = snap.now < w.start ? "in \(Say.duration(w.start.timeIntervalSince(snap.now)))"
            : "ends in \(Say.duration(w.end.timeIntervalSince(snap.now)))"
        return Chip(palette: palette, name: w.name, detail: long ? "\(Say.span(w)) · \(when)" : when, caution: true)
    }

    private func goodChip(_ w: TimingWindow) -> Chip {
        Chip(palette: palette, name: w.name, detail: snap.now < w.start ? Say.clock(w.start) : "now", caution: false)
    }

    private var medium: some View {
        HStack(alignment: .center, spacing: 14) {
            score(98)
            VStack(alignment: .leading, spacing: 0) {
                Eyebrow(text: dateLabel, color: palette.accent, size: 9.5)
                Spacer(minLength: 3).frame(maxHeight: 5)
                Text(today?.headline ?? "Open Siddha to see your day")
                    .font(Fonts.serif(16))
                    .foregroundStyle(palette.text)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
                Spacer(minLength: 3).frame(maxHeight: 5)
                if !panchangLine.isEmpty {
                    Text(panchangLine)
                        .font(Fonts.sans(10.5))
                        .foregroundStyle(palette.muted)
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                } else if today == nil {
                    Text(emptyHint)
                        .font(Fonts.sans(10.5))
                        .foregroundStyle(palette.muted)
                        .lineLimit(2)
                }
                if let line = today?.dos.first {
                    Spacer(minLength: 4).frame(maxHeight: 8)
                    row("Do", line, palette.good, size: 11.5)
                }
                Spacer(minLength: 6)
                chips
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .leading)
        }
    }

    private var emptyHint: String { "Your day’s score, tithi and timings show here." }

    @ViewBuilder private var large: some View {
        if today == nil {
            VStack(spacing: 10) {
                Spacer(minLength: 0)
                score(110)
                Eyebrow(text: dateLabel, color: palette.accent, size: 10)
                Text("Open Siddha to see your day")
                    .font(Fonts.serif(20))
                    .foregroundStyle(palette.text)
                Text(emptyHint)
                    .font(Fonts.sans(12.5))
                    .foregroundStyle(palette.muted)
                    .multilineTextAlignment(.center)
                Spacer(minLength: 0)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else {
            largeFilled
        }
    }

    private var largeFilled: some View {
        ViewThatFits(in: .vertical) {
            largeBody(items: 2, summary: true)
            largeBody(items: 1, summary: true)
            largeBody(items: 1, summary: false)
        }
    }

    private func largeBody(items: Int, summary: Bool) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 12) {
                score(80)
                VStack(alignment: .leading, spacing: 4) {
                    Eyebrow(text: dateLabel, color: palette.accent, size: 9.5)
                    Text(today?.headline ?? "Open Siddha to see your day")
                        .font(Fonts.serif(17))
                        .foregroundStyle(palette.text)
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            if let today {
                if summary, !today.summary.isEmpty {
                    Spacer(minLength: 8)
                    Text(today.summary)
                        .font(Fonts.sans(12.5))
                        .foregroundStyle(palette.muted)
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 8)
                panchangTiles(today)
                if !(today.dos.isEmpty && today.avoids.isEmpty) {
                    Spacer(minLength: 8)
                    doAvoid(today, items: items)
                }
                if let span = today.daySpan() {
                    Spacer(minLength: 10)
                    DayTimeline(palette: palette, windows: today.windows, span: span, now: snap.now)
                }
                Spacer(minLength: 8)
                chips
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private func panchangTiles(_ today: TodayPart) -> some View {
        let tiles = [("Tithi", today.tithi), ("Nakshatra", today.nakshatra), ("Yoga", today.yoga), ("Moon", today.moonSign)]
            .filter { !$0.1.isEmpty }
        return HStack(spacing: 5) {
            ForEach(tiles, id: \.0) { tile in
                VStack(alignment: .leading, spacing: 2) {
                    Text(tile.0.uppercased())
                        .font(Fonts.sans(8, .semibold))
                        .tracking(0.6)
                        .foregroundStyle(palette.muted)
                        .lineLimit(1)
                        .minimumScaleFactor(0.7)
                    Text(tile.1)
                        .font(Fonts.sans(11.5, .semibold))
                        .foregroundStyle(palette.text)
                        .lineLimit(2)
                        .minimumScaleFactor(0.85)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 7)
                .padding(.vertical, 6)
                .frame(maxHeight: .infinity, alignment: .topLeading)
                .background(RoundedRectangle(cornerRadius: 10, style: .continuous).fill(palette.glass))
                .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous).strokeBorder(palette.hairline, lineWidth: 0.6))
            }
        }
        .fixedSize(horizontal: false, vertical: true)
    }

    private func doAvoid(_ today: TodayPart, items: Int) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            ForEach(Array(today.dos.prefix(items).enumerated()), id: \.offset) { _, line in
                row("Do", line, palette.good)
            }
            ForEach(Array(today.avoids.prefix(items).enumerated()), id: \.offset) { _, line in
                row("Avoid", line, palette.bad)
            }
        }
    }

    private func row(_ label: String, _ text: String, _ color: Color, size: CGFloat = 12.5) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: size < 12 ? 6 : 8) {
            Text(label.uppercased())
                .font(Fonts.sans(8.5, .bold))
                .tracking(1)
                .foregroundStyle(color)
                .frame(width: size < 12 ? 22 : 42, alignment: .leading)
            Text(text)
                .font(Fonts.sans(size))
                .foregroundStyle(palette.text)
                .lineLimit(1)
        }
    }
}

/// Sunrise to the day's last window: take-care times in rose, good ones in
/// teal, and a mark for now.
struct DayTimeline: View {
    var palette: Palette
    var windows: [TimingWindow]
    var span: ClosedRange<Date>
    var now: Date

    var body: some View {
        VStack(spacing: 3) {
            GeometryReader { geo in
                let total = span.upperBound.timeIntervalSince(span.lowerBound)
                let x = { (d: Date) -> CGFloat in
                    CGFloat(max(0, min(1, d.timeIntervalSince(span.lowerBound) / total))) * geo.size.width
                }
                ZStack(alignment: .leading) {
                    Capsule().fill(palette.track)
                    ForEach(windows, id: \.self) { w in
                        Capsule()
                            .fill(w.caution ? palette.bad : palette.good)
                            .frame(width: max(4, x(w.end) - x(w.start)))
                            .offset(x: x(w.start))
                    }
                    if span.contains(now) {
                        RoundedRectangle(cornerRadius: 1)
                            .fill(palette.text)
                            .frame(width: 2, height: geo.size.height + 6)
                            .offset(x: x(now) - 1)
                    }
                }
            }
            .frame(height: 8)
            HStack {
                Text("Sunrise \(Say.clock(span.lowerBound))")
                Spacer()
                Text("Until \(Say.clock(span.upperBound))")
            }
            .font(Fonts.sans(9))
            .foregroundStyle(palette.muted)
        }
    }
}

// MARK: Calendar

struct CalendarFace: View {
    var snap: Snapshot
    var palette: Palette
    var size: Size

    var body: some View {
        switch size {
        case .small: small
        case .medium: medium
        case .large: large
        case .extraLarge: extraLarge
        }
    }

    private var cal: CalendarPart { snap.calendar ?? CalendarPart() }
    private var todayTithi: String { snap.freshToday?.tithi ?? cal.day(snap.iso)?.tithi ?? "" }

    private func quality(_ iso: String) -> String { cal.day(iso)?.quality ?? "" }

    private func tint(_ iso: String) -> Color {
        switch quality(iso) {
        case "good": return palette.goodSoft
        case "care": return palette.warnSoft
        default: return .clear
        }
    }

    private var small: some View {
        let event = cal.events(from: snap.iso, to: Days.from(snap.iso, count: 30).last ?? snap.iso).first
        return VStack(alignment: .leading, spacing: 0) {
            Eyebrow(text: Say.date(snap.iso, "EEE · MMMM"), color: palette.accent, size: 9.5)
            Text(Say.date(snap.iso, "d"))
                .font(Fonts.serif(40))
                .foregroundStyle(palette.text)
                .padding(.top, 2)
            Text(todayTithi.isEmpty ? "Open Siddha" : todayTithi)
                .font(Fonts.sans(11.5, .semibold))
                .foregroundStyle(palette.text)
                .lineLimit(1)
                .minimumScaleFactor(0.8)
            Spacer(minLength: 4)
            if let event {
                Text(event.date == snap.iso ? event.text : "\(event.text) · \(Say.daysUntil(from: snap.iso, to: event.date))")
                    .font(Fonts.sans(10.5, .medium))
                    .foregroundStyle(palette.accent)
                    .lineLimit(2)
            } else if let q = qualityWord(snap.iso) {
                Text(q.0).font(Fonts.sans(10.5, .semibold)).foregroundStyle(q.1)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private func qualityWord(_ iso: String) -> (String, Color)? {
        switch quality(iso) {
        case "good": return ("Good day for you", palette.good)
        case "care": return ("Take care today", palette.warn)
        default: return nil
        }
    }

    private var week: [String] { Days.from(snap.iso, count: 7) }

    private func header(_ title: String) -> some View {
        HStack(alignment: .firstTextBaseline) {
            Text(title).font(Fonts.serif(15)).foregroundStyle(palette.text)
            Spacer(minLength: 8)
            Text(snap.freshToday?.masa.isEmpty == false ? snap.freshToday!.masa : (todayTithi.isEmpty ? "" : "Today: \(todayTithi)"))
                .font(Fonts.sans(10))
                .foregroundStyle(palette.muted)
                .lineLimit(1)
        }
    }

    private var strip: some View {
        let marked = cal.marked(from: week.first ?? snap.iso, to: week.last ?? snap.iso)
        return HStack(spacing: 4) {
            ForEach(week, id: \.self) { iso in
                VStack(spacing: 1) {
                    Text(iso == snap.iso ? "Today" : Say.date(iso, "EEE"))
                        .font(Fonts.sans(8.5, iso == snap.iso ? .semibold : .regular))
                        .foregroundStyle(iso == snap.iso ? palette.text : palette.muted)
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)
                    Text(Say.date(iso, "d"))
                        .font(Fonts.sans(15, .semibold))
                        .foregroundStyle(palette.text)
                        .monospacedDigit()
                    Text(Say.shortTithi(cal.day(iso)?.tithi ?? ""))
                        .font(Fonts.sans(7.5))
                        .foregroundStyle(palette.muted)
                        .lineLimit(1)
                        .minimumScaleFactor(0.6)
                        .padding(.horizontal, 2)
                    Circle()
                        .fill(marked.contains(iso) ? palette.accent : .clear)
                        .frame(width: 4, height: 4)
                }
                .padding(.vertical, 5)
                .frame(maxWidth: .infinity)
                .background(RoundedRectangle(cornerRadius: 9, style: .continuous).fill(tint(iso)))
                .overlay(RoundedRectangle(cornerRadius: 9, style: .continuous)
                    .strokeBorder(iso == snap.iso ? palette.accent : .clear, lineWidth: 1.4))
            }
        }
    }

    private func eventRows(_ events: [DayEvent], limit: Int) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            if events.isEmpty {
                Text(nextLine.isEmpty ? "No festivals this week" : "Next: \(nextLine)")
                    .font(Fonts.sans(11))
                    .foregroundStyle(palette.muted)
                    .lineLimit(1)
            }
            ForEach(events.prefix(limit), id: \.self) { e in
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Text(e.date == snap.iso ? "Today" : Say.date(e.date, "EEE d"))
                        .font(Fonts.sans(11, .bold))
                        .foregroundStyle(palette.accent)
                        .frame(width: 44, alignment: .leading)
                    (Text(e.text).foregroundColor(palette.text)
                        + Text(e.approx ? " · varies by tradition" : "").foregroundColor(palette.muted))
                        .font(Fonts.sans(11))
                        .lineLimit(1)
                }
            }
        }
    }

    /// The next festival or moon day past this week, for a quiet week.
    private var nextLine: String {
        let horizon = Days.from(snap.iso, count: 60).last ?? snap.iso
        guard let e = cal.events(from: snap.iso, to: horizon).first else { return "" }
        return "\(e.text) · \(Say.daysUntil(from: snap.iso, to: e.date))"
    }

    private var medium: some View {
        VStack(alignment: .leading, spacing: 0) {
            header("This week")
            Spacer(minLength: 6)
            strip
            Spacer(minLength: 6)
            eventRows(cal.events(from: week.first ?? snap.iso, to: week.last ?? snap.iso), limit: 2)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private func monthGrid(cellFont: CGFloat) -> some View {
        let month = Days.month(of: snap.iso)
        let monthDays = month.weeks.flatMap { $0 }.compactMap { $0 }
        let marked = cal.marked(from: monthDays.first ?? snap.iso, to: monthDays.last ?? snap.iso)
        return VStack(spacing: 3) {
            HStack(spacing: 3) {
                ForEach(Array(["S", "M", "T", "W", "T", "F", "S"].enumerated()), id: \.offset) { _, d in
                    Text(d).font(Fonts.sans(9, .semibold)).foregroundStyle(palette.muted).frame(maxWidth: .infinity)
                }
            }
            ForEach(Array(month.weeks.enumerated()), id: \.offset) { _, week in
                HStack(spacing: 3) {
                    ForEach(Array(week.enumerated()), id: \.offset) { _, iso in
                        ZStack(alignment: .bottom) {
                            RoundedRectangle(cornerRadius: 7, style: .continuous)
                                .fill(iso.map(tint) ?? .clear)
                            RoundedRectangle(cornerRadius: 7, style: .continuous)
                                .strokeBorder(iso == snap.iso ? palette.accent : .clear, lineWidth: 1.4)
                            if let iso {
                                Text(Say.date(iso, "d"))
                                    .font(Fonts.sans(cellFont, iso == snap.iso ? .bold : .medium))
                                    .foregroundStyle(iso < snap.iso ? palette.muted : palette.text)
                                    .monospacedDigit()
                                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                                if marked.contains(iso) {
                                    Circle().fill(palette.accent).frame(width: 3.5, height: 3.5).padding(.bottom, 2.5)
                                }
                            }
                        }
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                    }
                }
            }
        }
    }

    private var legend: some View {
        HStack(spacing: 10) {
            legendItem(palette.goodSoft, "Good day")
            legendItem(palette.warnSoft, "Take care")
            HStack(spacing: 4) {
                Circle().fill(palette.accent).frame(width: 4, height: 4)
                Text("Festival")
            }
        }
        .font(Fonts.sans(9))
        .foregroundStyle(palette.muted)
    }

    private func legendItem(_ color: Color, _ text: String) -> some View {
        HStack(spacing: 4) {
            RoundedRectangle(cornerRadius: 2).fill(color).frame(width: 9, height: 9)
            Text(text)
        }
    }

    private var monthEvents: [DayEvent] {
        cal.events(from: snap.iso, to: Days.from(snap.iso, count: 45).last ?? snap.iso)
    }

    private var large: some View {
        VStack(alignment: .leading, spacing: 0) {
            header(Days.month(of: snap.iso).title)
            Spacer(minLength: 6).frame(maxHeight: 8)
            monthGrid(cellFont: 12.5)
                .frame(maxHeight: .infinity)
            Spacer(minLength: 8).frame(maxHeight: 10)
            let events = Array(monthEvents.prefix(4))
            LazyVGrid(columns: [GridItem(.flexible(), spacing: 10, alignment: .leading), GridItem(.flexible(), alignment: .leading)],
                      alignment: .leading, spacing: 4) {
                ForEach(events, id: \.self) { e in
                    HStack(alignment: .firstTextBaseline, spacing: 6) {
                        Text(e.date == snap.iso ? "Today" : Say.date(e.date, "EEE d"))
                            .font(Fonts.sans(10.5, .bold))
                            .foregroundStyle(palette.accent)
                        Text(e.text).font(Fonts.sans(10.5)).foregroundStyle(palette.text).lineLimit(1)
                    }
                }
            }
            Spacer(minLength: 6).frame(maxHeight: 8)
            legend
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private var extraLarge: some View {
        HStack(alignment: .top, spacing: 18) {
            VStack(alignment: .leading, spacing: 8) {
                Text(Days.month(of: snap.iso).title).font(Fonts.serif(17)).foregroundStyle(palette.text)
                monthGrid(cellFont: 13).frame(maxHeight: .infinity)
                legend
            }
            .frame(maxWidth: .infinity)
            VStack(alignment: .leading, spacing: 0) {
                header("This week")
                Spacer(minLength: 8).frame(maxHeight: 12)
                strip
                Spacer(minLength: 10).frame(maxHeight: 14)
                Eyebrow(text: "Coming up", color: palette.accent, size: 9)
                Spacer(minLength: 6).frame(maxHeight: 8)
                eventRows(monthEvents, limit: 6)
                Spacer(minLength: 10)
                todayTimings
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
    }
}

extension CalendarFace {
    /// The iPad card's last block: today's timings, so the week column ends
    /// on something useful rather than an empty band.
    @ViewBuilder fileprivate var todayTimings: some View {
        if let today = snap.freshToday, !today.windows.isEmpty {
            VStack(alignment: .leading, spacing: 5) {
                Eyebrow(text: "Today's timings", color: palette.accent, size: 9)
                LazyVGrid(columns: [GridItem(.flexible(), spacing: 10, alignment: .leading), GridItem(.flexible(), alignment: .leading)],
                          alignment: .leading, spacing: 4) {
                    ForEach(today.windows.prefix(4), id: \.self) { w in
                        HStack(alignment: .firstTextBaseline, spacing: 6) {
                            Circle().fill(w.caution ? palette.bad : palette.good).frame(width: 6, height: 6)
                            Text(w.name).font(Fonts.sans(11, .semibold)).foregroundStyle(palette.text)
                            Text(Say.span(w)).font(Fonts.sans(11)).foregroundStyle(palette.muted)
                        }
                        .lineLimit(1)
                    }
                }
            }
        }
    }
}

// MARK: Timing, moon, mantra, listen, ask

struct TimingFace: View {
    var snap: Snapshot
    var palette: Palette

    var body: some View {
        let today = snap.freshToday
        let window = today?.currentWindow(at: snap.now)
        VStack(alignment: .leading, spacing: 0) {
            Eyebrow(text: window?.name ?? (today == nil ? "Timing" : "Today’s windows"),
                    color: window.map { $0.caution ? palette.accent : palette.good } ?? palette.accent, size: 9.5)
            Spacer(minLength: 4)
            if let window {
                let running = snap.now >= window.start
                Text(running ? "Ends in" : "Starts in")
                    .font(Fonts.serif(17))
                    .foregroundStyle(palette.text)
                Text(timerInterval: snap.now...(running ? window.end : window.start), countsDown: true)
                    .font(Fonts.serif(25))
                    .foregroundStyle(palette.text)
                    .monospacedDigit()
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
                Text(Say.span(window))
                    .font(Fonts.sans(11))
                    .foregroundStyle(palette.muted)
                    .padding(.top, 2)
                Spacer(minLength: 4)
                if let good = today?.nextGood(at: snap.now, after: window.caution ? window : nil), good != window {
                    Text("Next good: \(good.name) \(Say.clock(good.start))")
                        .font(Fonts.sans(10, .medium))
                        .foregroundStyle(palette.good)
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)
                }
            } else {
                Text(today == nil ? "Open Siddha for today" : "All done for today")
                    .font(Fonts.serif(17))
                    .foregroundStyle(palette.text)
                Spacer(minLength: 4)
                Text(today == nil ? "" : "Tomorrow’s appear at midnight")
                    .font(Fonts.sans(10.5))
                    .foregroundStyle(palette.muted)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }
}

struct MoonFace: View {
    var snap: Snapshot
    var palette: Palette

    var body: some View {
        let next = snap.calendar?.nextMoon(from: snap.iso)
        VStack(spacing: 0) {
            MoonDisc(palette: palette, date: snap.now, tithi: snap.freshToday?.tithi, size: 58)
            Spacer(minLength: 8)
            Text(snap.freshToday?.tithi ?? "The moon today")
                .font(Fonts.serif(15))
                .foregroundStyle(palette.text)
                .lineLimit(1)
                .minimumScaleFactor(0.8)
            Spacer(minLength: 3)
            if let next {
                Text(next.full ? "PURNIMA" : "AMAVASYA")
                    .font(Fonts.sans(8.5, .bold))
                    .tracking(1.2)
                    .foregroundStyle(palette.gold)
                Text(next.date == snap.iso ? "Today" : "\(Say.date(next.date, "EEE d MMM")) · \(Say.daysUntil(from: snap.iso, to: next.date))")
                    .font(Fonts.sans(10.5))
                    .foregroundStyle(palette.muted)
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct MantraFace<Counter: View>: View {
    var snap: Snapshot
    var palette: Palette
    /// Wraps the ring: on iPhone a tap on it counts one (CountMantraIntent).
    var counter: (AnyView) -> Counter

    var body: some View {
        let mantra = snap.mantra
        let target = mantra?.target ?? 108
        let count = snap.mantraCount
        let done = count >= target
        VStack(spacing: 0) {
            Eyebrow(text: mantra?.title ?? "Mantra", color: palette.accent, size: 8.5)
            Spacer(minLength: 6)
            counter(AnyView(
                ZStack {
                    Ring(progress: Double(count) / Double(target), color: done ? palette.good : palette.accent,
                         track: palette.track, width: 7)
                    VStack(spacing: 0) {
                        Text(mantra == nil ? "ॐ" : "\(count)")
                            .font(Fonts.serif(24))
                            .foregroundStyle(palette.text)
                            .monospacedDigit()
                        if mantra != nil {
                            Text("of \(target)").font(Fonts.sans(9)).foregroundStyle(palette.muted)
                        }
                    }
                }
                .frame(width: 74, height: 74)
            ))
            Spacer(minLength: 6)
            Text(mantra == nil ? "Choose a mantra in Siddha" : done ? "Completed today" : count == 0 ? "Tap the ring to count" : "\(target - count) to go")
                .font(Fonts.sans(10.5))
                .foregroundStyle(palette.muted)
                .lineLimit(1)
                .minimumScaleFactor(0.8)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct PlayButton: View {
    var palette: Palette
    var size: CGFloat

    var body: some View {
        ZStack {
            Circle().fill(palette.primary)
            Circle().strokeBorder(Color.white.opacity(0.45), lineWidth: 0.8)
            Path { p in
                let w = size * 0.3
                p.move(to: CGPoint(x: size * 0.4, y: size / 2 - w / 2))
                p.addLine(to: CGPoint(x: size * 0.4 + w * 0.9, y: size / 2))
                p.addLine(to: CGPoint(x: size * 0.4, y: size / 2 + w / 2))
                p.closeSubpath()
            }
            .fill(palette.onAccent)
        }
        .frame(width: size, height: size)
        .shadow(color: palette.accent.opacity(0.35), radius: 6, y: 3)
    }
}

struct ListenFace: View {
    var snap: Snapshot
    var palette: Palette

    var body: some View {
        let today = snap.freshToday
        VStack(spacing: 0) {
            PlayButton(palette: palette, size: 48)
            Spacer(minLength: 8)
            Text("Listen to your day")
                .font(Fonts.sans(13, .semibold))
                .foregroundStyle(palette.text)
                .lineLimit(1)
                .minimumScaleFactor(0.85)
            Spacer(minLength: 3)
            Text(today.map { "\($0.label.isEmpty ? "Today" : $0.label + " day") · \(Say.listenLength($0.listen))" } ?? "Siddha reads your day")
                .font(Fonts.sans(10.5))
                .foregroundStyle(palette.muted)
                .lineLimit(1)
                .minimumScaleFactor(0.8)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct Orb: View {
    var size: CGFloat

    var body: some View {
        Circle()
            .fill(RadialGradient(colors: [Color(hex: 0xF6D98E), Color(hex: 0xB07A2A), Color(hex: 0x4A2F12)],
                                 center: UnitPoint(x: 0.35, y: 0.3), startRadius: 0, endRadius: size * 0.7))
            .overlay(Circle().strokeBorder(Color.white.opacity(0.35), lineWidth: 0.6))
            .frame(width: size, height: size)
            .shadow(color: Color(hex: 0xB07A2A).opacity(0.4), radius: size * 0.2)
    }
}

struct AskFace: View {
    var palette: Palette

    var body: some View {
        VStack(spacing: 0) {
            Orb(size: 46)
            Spacer(minLength: 8)
            Text("Ask Siddha")
                .font(Fonts.serif(17))
                .foregroundStyle(palette.text)
            Spacer(minLength: 3)
            Text("About your day, work, money or family")
                .font(Fonts.sans(10.5))
                .foregroundStyle(palette.muted)
                .multilineTextAlignment(.center)
                .lineLimit(2)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: Subhashita

struct SubhashitaFace: View {
    var snap: Snapshot
    var palette: Palette
    var size: Size

    var body: some View {
        if let verse = snap.verse {
            size == .medium ? AnyView(medium(verse)) : AnyView(large(verse))
        } else {
            AnyView(VStack(alignment: .leading, spacing: 0) {
                Eyebrow(text: "Today’s Subhashita", color: palette.accent, size: 9.5)
                Spacer(minLength: 6)
                Text("A verse a day from the Bhagavad Gita, Chanakya Niti and the Puranas.")
                    .font(Fonts.serifItalic(15))
                    .foregroundStyle(palette.text)
                Spacer(minLength: 6)
                Text("Open Siddha to load today’s verse").font(Fonts.sans(10.5)).foregroundStyle(palette.muted)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading))
        }
    }

    private func top(_ verse: Verse, date: Bool) -> some View {
        HStack {
            Eyebrow(text: date ? "Today’s Subhashita · " + Say.date(verse.date, "d MMM") : "Today’s Subhashita",
                    color: palette.accent, size: 9.5)
            Spacer()
            Image(systemName: "square.and.arrow.up")
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(palette.muted)
        }
    }

    private func source(_ verse: Verse) -> some View {
        Eyebrow(text: "\(verse.source) \(verse.ref)", color: palette.gold, size: 9)
    }

    private func medium(_ verse: Verse) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            top(verse, date: false)
            Spacer(minLength: 5)
            if !verse.firstLine.isEmpty {
                Text(verse.firstLine)
                    .font(Fonts.sans(11.5))
                    .foregroundStyle(palette.muted)
                    .lineLimit(1)
                Spacer(minLength: 4).frame(maxHeight: 6)
            }
            Text(verse.meaning.isEmpty ? verse.english : verse.meaning)
                .font(Fonts.serifItalic(15.5))
                .foregroundStyle(palette.text)
                .lineLimit(3)
                .minimumScaleFactor(0.85)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 5)
            source(verse)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    /// Bigger type when the verse is short enough, so a short verse fills
    /// the card instead of leaving gaps between its parts.
    private func large(_ verse: Verse) -> some View {
        ViewThatFits(in: .vertical) {
            large(verse, scale: 1.3)
            large(verse, scale: 1.15)
            large(verse, scale: 1)
        }
    }

    private func large(_ verse: Verse, scale: CGFloat) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            top(verse, date: true)
            Spacer(minLength: 8)
            if !verse.sanskrit.isEmpty {
                Text(verse.sanskrit.trimmingCharacters(in: .whitespacesAndNewlines))
                    .font(Fonts.sans(13.5 * scale))
                    .foregroundStyle(palette.muted)
                    .lineSpacing(3)
                    .lineLimit(scale > 1 ? nil : 4)
                    .fixedSize(horizontal: false, vertical: true)
                Spacer(minLength: 8 * scale)
            }
            if !verse.english.isEmpty {
                Text("“\(verse.english)”")
                    .font(Fonts.serifItalic(18 * scale))
                    .foregroundStyle(palette.text)
                    .lineLimit(scale > 1 ? nil : 4)
                    .fixedSize(horizontal: false, vertical: true)
                Spacer(minLength: 8 * scale)
            }
            if !verse.meaning.isEmpty {
                Eyebrow(text: "Meaning", color: palette.gold, size: 8.5)
                Text(verse.meaning)
                    .font(Fonts.sans(13 * scale))
                    .foregroundStyle(palette.text)
                    .lineLimit(scale > 1 ? nil : 4)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(.top, 3)
                Spacer(minLength: 8 * scale)
            }
            source(verse)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }
}
