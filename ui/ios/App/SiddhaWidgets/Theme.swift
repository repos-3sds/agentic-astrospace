import CoreText
import SwiftUI

// The app's two looks (ui/src/styles-mobile.scss): "Cream Glass" by day and
// "Liquid Glass" by night. A widget can't see the app's glowing ground behind
// it, so each card carries the theme's light inside it, under the same glossy
// glass recipe the app's cards use: a diagonal sheen, a bright top edge and a
// fine hairline. Widgets follow the phone's light or dark setting.

extension Color {
    init(hex: UInt32, alpha: Double = 1) {
        self.init(.sRGB,
                  red: Double((hex >> 16) & 0xFF) / 255,
                  green: Double((hex >> 8) & 0xFF) / 255,
                  blue: Double(hex & 0xFF) / 255,
                  opacity: alpha)
    }
}

struct Palette {
    var dark: Bool
    var text: Color
    var muted: Color
    var accent: Color
    var onAccent: Color
    var gold: Color
    var track: Color
    var glass: Color
    var hairline: Color
    var sheen: Color
    var good: Color
    var goodSoft: Color
    var warn: Color
    var warnSoft: Color
    var bad: Color
    var badSoft: Color
    var moonDark: Color
    var moonLit: Color
    var base: [Color]
    /// The theme's lights inside the card: colour, centre, radius as a share of the card.
    var lights: [(Color, UnitPoint, CGFloat)]
    var gloss: [Color]

    static let day = Palette(
        dark: false,
        text: Color(hex: 0x201A14), muted: Color(hex: 0x6E6457),
        accent: Color(hex: 0xB13F2E), onAccent: Color(hex: 0xFFF8EC), gold: Color(hex: 0x7A5218),
        track: Color(hex: 0x785A32, alpha: 0.15), glass: Color.white.opacity(0.62),
        hairline: Color.white.opacity(0.95), sheen: .white,
        good: Color(hex: 0x2F7D57), goodSoft: Color(hex: 0x2F7D57, alpha: 0.14),
        warn: Color(hex: 0x8A5210), warnSoft: Color(hex: 0x8A5210, alpha: 0.13),
        bad: Color(hex: 0xA33A3A), badSoft: Color(hex: 0xA33A3A, alpha: 0.12),
        moonDark: Color(hex: 0xE7DCCB), moonLit: Color(hex: 0xC9A15A),
        base: [Color(hex: 0xFFFDF8), Color(hex: 0xFAF1E3)],
        lights: [
            (Color(hex: 0xFFC478, alpha: 0.55), UnitPoint(x: 0.92, y: 0), 0.75),
            (Color(hex: 0xE88C6E, alpha: 0.22), UnitPoint(x: 0, y: 1), 0.7),
        ],
        gloss: [Color.white.opacity(0.85), Color.white.opacity(0.25), Color.white.opacity(0)]
    )

    static let night = Palette(
        dark: true,
        text: Color(hex: 0xF7F7F8), muted: Color(hex: 0xA8A8B3),
        accent: Color(hex: 0xFF9B85), onAccent: Color(hex: 0x1C0A08), gold: Color(hex: 0xF3C77A),
        track: Color.white.opacity(0.1), glass: Color.white.opacity(0.09),
        hairline: Color.white.opacity(0.16), sheen: Color.white.opacity(0.34),
        good: Color(hex: 0x5EEAD4), goodSoft: Color(hex: 0x5EEAD4, alpha: 0.13),
        warn: Color(hex: 0xFCD34D), warnSoft: Color(hex: 0xFCD34D, alpha: 0.13),
        bad: Color(hex: 0xFDA4AF), badSoft: Color(hex: 0xFDA4AF, alpha: 0.13),
        moonDark: Color.white.opacity(0.1), moonLit: Color(hex: 0xF3E3B8),
        base: [Color(hex: 0x1A1A1E), Color(hex: 0x0A0A0C)],
        lights: [
            (Color(hex: 0xFF7896, alpha: 0.38), UnitPoint(x: 0.95, y: 0), 0.8),
            (Color(hex: 0xFFAA5A, alpha: 0.24), UnitPoint(x: 0, y: 0.7), 0.75),
            (Color(hex: 0x6E8CFF, alpha: 0.26), UnitPoint(x: 1, y: 1), 0.75),
        ],
        gloss: [Color.white.opacity(0.22), Color.white.opacity(0.06), Color.white.opacity(0)]
    )

    static func of(_ scheme: ColorScheme) -> Palette { scheme == .dark ? .night : .day }

    /// The score ring's colour by band, as the Today dial.
    func band(_ band: String) -> Color {
        switch band {
        case "tough": return bad
        case "mixed": return warn
        default: return good
        }
    }

    var primary: LinearGradient {
        dark ? LinearGradient(colors: [Color(hex: 0xFFB48A), Color(hex: 0xFF7A8A)], startPoint: .topLeading, endPoint: .bottomTrailing)
            : LinearGradient(colors: [accent, accent], startPoint: .top, endPoint: .bottom)
    }
}

/// The card itself, drawn as the widget's container background.
struct GlassCard: View {
    var palette: Palette
    /// The reader's opacity setting (Settings > Widgets), 0 to 1.
    var opacity: Double = 1

    var body: some View {
        GeometryReader { geo in
            let size = max(geo.size.width, geo.size.height)
            ZStack {
                LinearGradient(colors: palette.base, startPoint: .top, endPoint: .bottom)
                ForEach(Array(palette.lights.enumerated()), id: \.offset) { _, light in
                    RadialGradient(colors: [light.0, light.0.opacity(0)], center: light.1,
                                   startRadius: 0, endRadius: size * light.2)
                }
                LinearGradient(stops: [
                    .init(color: palette.gloss[0], location: 0),
                    .init(color: palette.gloss[1], location: 0.3),
                    .init(color: palette.gloss[2], location: 0.5),
                ], startPoint: .topLeading, endPoint: .bottomTrailing)
                // The bright top edge that makes glass read as glass.
                VStack(spacing: 0) {
                    LinearGradient(colors: [palette.sheen.opacity(0), palette.sheen, palette.sheen.opacity(0)],
                                   startPoint: .leading, endPoint: .trailing)
                        .frame(height: 1)
                        .padding(.horizontal, geo.size.width * 0.08)
                    Spacer(minLength: 0)
                }
            }
            .opacity(0.25 + 0.75 * opacity)
        }
    }
}

enum Fonts {
    /// Registers the bundled Playfair files once per process. Info.plist's
    /// UIAppFonts names them too; this also covers the Mac preview renderer.
    static func register(from bundle: Bundle = .main) {
        guard !registered else { return }
        registered = true
        for url in bundle.urls(forResourcesWithExtension: "ttf", subdirectory: nil) ?? [] {
            CTFontManagerRegisterFontsForURL(url as CFURL, .process, nil)
        }
    }

    private static var registered = false

    /// Playfair Display, bundled (UIAppFonts), for headlines and numbers.
    static func serif(_ size: CGFloat) -> Font { .custom("PlayfairDisplay-Regular", size: size) }
    static func serifItalic(_ size: CGFloat) -> Font { .custom("PlayfairDisplay-Italic", size: size) }
    /// The system face for everything else, as an iPhone reader expects.
    static func sans(_ size: CGFloat, _ weight: Font.Weight = .regular) -> Font { .system(size: size, weight: weight) }
}

/// Small capitals label: "YOUR DAY · SAT 18 OCT".
struct Eyebrow: View {
    var text: String
    var color: Color
    var size: CGFloat = 10

    var body: some View {
        Text(text.uppercased())
            .font(Fonts.sans(size, .semibold))
            .tracking(size * 0.14)
            .foregroundStyle(color)
            .lineLimit(1)
    }
}

struct Ring: View {
    var progress: Double
    var color: Color
    var track: Color
    var width: CGFloat

    var body: some View {
        ZStack {
            Circle().stroke(track, lineWidth: width)
            if progress > 0 {
                Circle()
                    .trim(from: 0, to: min(1, progress))
                    .stroke(color, style: StrokeStyle(lineWidth: width, lineCap: .round))
                    .rotationEffect(.degrees(-90))
            }
        }
        .padding(width / 2)
    }
}

/// The day score: ring, number and the band's word, as the Today dial.
struct ScoreRing: View {
    var palette: Palette
    var score: Int?
    var label: String
    var band: String
    var size: CGFloat

    var body: some View {
        let color = palette.band(band)
        ZStack {
            Ring(progress: Double(score ?? 0) / 100, color: color, track: palette.track, width: size * 0.085)
            VStack(spacing: 1) {
                Text(score.map(String.init) ?? "–")
                    .font(Fonts.serif(size * 0.32))
                    .foregroundStyle(palette.text)
                    .monospacedDigit()
                if !label.isEmpty {
                    Text(label.uppercased())
                        .font(Fonts.sans(size * 0.095, .bold))
                        .tracking(size * 0.012)
                        .foregroundStyle(color)
                        .lineLimit(1)
                        .minimumScaleFactor(0.7)
                }
            }
        }
        .frame(width: size, height: size)
    }
}

/// A frosted pill: "Rahu Kalam 9:15–10:40 · in 55m".
struct Chip: View {
    var palette: Palette
    var name: String
    var detail: String
    var caution: Bool

    var body: some View {
        (Text(name).font(Fonts.sans(11, .bold)).foregroundColor(caution ? palette.bad : palette.good)
            + Text(detail.isEmpty ? "" : " " + detail).font(Fonts.sans(11, .medium)).foregroundColor(palette.text))
            .lineLimit(1)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(Capsule().fill(palette.glass))
            .overlay(Capsule().strokeBorder(palette.hairline, lineWidth: 0.6))
    }
}

/// A small clock glyph and one timing line, in gold.
struct TimingLine: View {
    var palette: Palette
    var text: String
    var size: CGFloat = 11

    var body: some View {
        HStack(spacing: 5) {
            Circle().strokeBorder(palette.gold, lineWidth: 1.4).frame(width: size - 1, height: size - 1)
            Text(text).font(Fonts.sans(size, .medium)).foregroundStyle(palette.gold).lineLimit(1)
        }
    }
}

/// The moon's shape for a moment: dark disc, lit part bounded by the
/// terminator. Only the drawing is approximate; dates come from the app.
struct MoonShape: Shape {
    /// 0 new, 0.5 full, back to 1.
    var phase: Double

    func path(in rect: CGRect) -> Path {
        let r = min(rect.width, rect.height) / 2
        let c = CGPoint(x: rect.midX, y: rect.midY)
        let side: CGFloat = phase < 0.5 ? 1 : -1      // waxing lit on the right
        let k = CGFloat(cos(2 * Double.pi * phase))  // 1 new, -1 full
        var path = Path()
        let steps = 48
        for i in 0...steps {
            let t = Double.pi * Double(i) / Double(steps)
            let p = CGPoint(x: c.x + side * r * CGFloat(sin(t)), y: c.y - r * CGFloat(cos(t)))
            if i == 0 { path.move(to: p) } else { path.addLine(to: p) }
        }
        for i in stride(from: steps, through: 0, by: -1) {
            let t = Double.pi * Double(i) / Double(steps)
            path.addLine(to: CGPoint(x: c.x + side * k * r * CGFloat(sin(t)), y: c.y - r * CGFloat(cos(t))))
        }
        path.closeSubpath()
        return path
    }

    /// The phase for the day's tithi, so the drawing agrees with the words
    /// beside it: the middle of the tithi's twelve degrees. Nil when the name
    /// is not one we know, and the date is used instead.
    static func phase(tithi: String) -> Double? {
        let words = tithi.lowercased().split(separator: " ").map(String.init)
        guard let name = words.last else { return nil }
        if name.hasPrefix("purn") { return 14.5 / 30 }
        if name.hasPrefix("amav") { return 29.5 / 30 }
        let order: [[String]] = [["prati"], ["dwi", "dvi"], ["tri", "trit"], ["chaturth"], ["pancham"],
                                 ["shash", "sasht", "sast"], ["sapt"], ["asht"], ["nav"], ["dash"],
                                 ["ekad"], ["dwad", "dvad"], ["trayo"], ["chaturd"]]
        guard let index = order.firstIndex(where: { $0.contains(where: name.hasPrefix) }) else { return nil }
        let krishna = words.contains { $0.hasPrefix("krishna") || $0.hasPrefix("krsna") || $0.hasPrefix("bahula") }
        return (Double(index + 1 + (krishna ? 15 : 0)) - 0.5) / 30
    }

    /// The tithi's phase when there is one, else the date's.
    static func phase(tithi: String?, at date: Date) -> Double {
        tithi.flatMap { phase(tithi: $0) } ?? phase(at: date)
    }

    /// 2000-01-06 18:14 UTC was a new moon; 29.530589 days per lunation.
    static func phase(at date: Date) -> Double {
        let days = (date.timeIntervalSince1970 - 947_182_440) / 86_400
        let age = days.truncatingRemainder(dividingBy: 29.530589)
        return (age < 0 ? age + 29.530589 : age) / 29.530589
    }
}

struct MoonDisc: View {
    var palette: Palette
    var date: Date
    var tithi: String? = nil
    var size: CGFloat

    var body: some View {
        ZStack {
            Circle().fill(palette.moonDark)
            MoonShape(phase: MoonShape.phase(tithi: tithi, at: date)).fill(palette.moonLit)
        }
        .frame(width: size, height: size)
        .shadow(color: palette.moonLit.opacity(palette.dark ? 0.35 : 0.2), radius: size * 0.12)
    }
}
