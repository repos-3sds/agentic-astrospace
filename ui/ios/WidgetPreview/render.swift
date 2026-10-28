import AppKit
import CoreText
import SwiftUI

// Renders every widget face, in both themes, at iPhone sizes, so a change to
// the widgets can be looked at before it reaches a phone (CLAUDE.md: verify
// visually, not just by build). The faces are the extension's own views
// (ui/ios/App/SiddhaWidgets/Views.swift) on the illustrative day in
// Sample.swift, at 8:20 in the morning. Runs on a Mac (CI: ios-launch.yml):
//
//   swiftc -parse-as-library \
//     ui/ios/App/Shared/WidgetGroup.swift ui/ios/App/SiddhaWidgets/{Model,Theme,Views,Sample}.swift \
//     ui/ios/WidgetPreview/render.swift -o /tmp/render
//   /tmp/render out-dir ui/ios/App/SiddhaWidgets/Fonts
//
// Widget sizes are those of a 6.1" iPhone (393 points wide); content sits
// inside WidgetKit's default 16-point margins, as on the phone.

struct Face {
    var name: String
    var width: CGFloat
    var height: CGFloat
    var view: (Snapshot, Palette) -> AnyView
}

let small = CGSize(width: 158, height: 158)
let medium = CGSize(width: 338, height: 158)
let large = CGSize(width: 338, height: 354)
let extraLarge = CGSize(width: 715, height: 330)

func face<V: View>(_ name: String, _ size: CGSize, _ view: @escaping (Snapshot, Palette) -> V) -> Face {
    Face(name: name, width: size.width, height: size.height) { AnyView(view($0, $1)) }
}

let faces: [Face] = [
    face("today-small", small) { TodayFace(snap: $0, palette: $1, size: .small) },
    face("today-medium", medium) { TodayFace(snap: $0, palette: $1, size: .medium) },
    face("today-large", large) { TodayFace(snap: $0, palette: $1, size: .large) },
    face("calendar-small", small) { CalendarFace(snap: $0, palette: $1, size: .small) },
    face("calendar-medium", medium) { CalendarFace(snap: $0, palette: $1, size: .medium) },
    face("calendar-large", large) { CalendarFace(snap: $0, palette: $1, size: .large) },
    face("calendar-ipad", extraLarge) { CalendarFace(snap: $0, palette: $1, size: .extraLarge) },
    face("timing-small", small) { TimingFace(snap: $0, palette: $1) },
    face("moon-small", small) { MoonFace(snap: $0, palette: $1) },
    face("mantra-small", small) { MantraFace(snap: $0, palette: $1) { $0 } },
    face("listen-small", small) { ListenFace(snap: $0, palette: $1) },
    face("ask-small", small) { AskFace(palette: $1) },
    face("subhashita-medium", medium) { SubhashitaFace(snap: $0, palette: $1, size: .medium) },
    face("subhashita-large", large) { SubhashitaFace(snap: $0, palette: $1, size: .large) },
]

@MainActor
func card(_ f: Face, _ snap: Snapshot, _ scheme: ColorScheme) -> some View {
    let palette = Palette.of(scheme)
    return ZStack {
        GlassCard(palette: palette, opacity: snap.opacity)
        f.view(snap, palette).padding(16)
    }
    .frame(width: f.width, height: f.height)
    .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
    .overlay(RoundedRectangle(cornerRadius: 22, style: .continuous).strokeBorder(palette.hairline, lineWidth: 1))
    .environment(\.colorScheme, scheme)
}

@MainActor
func write(_ view: some View, to url: URL) {
    let renderer = ImageRenderer(content: view)
    renderer.scale = 3
    guard let image = renderer.cgImage else { return print("could not render \(url.lastPathComponent)") }
    let rep = NSBitmapImageRep(cgImage: image)
    try? rep.representation(using: .png, properties: [:])?.write(to: url)
    print("wrote \(url.path)")
}

/// A whole "home screen" per theme: every face on a wallpaper, for one look.
@MainActor
func sheet(_ snap: Snapshot, _ scheme: ColorScheme, _ list: [Face]) -> some View {
    let wallpaper = scheme == .dark
        ? LinearGradient(colors: [Color(hex: 0x1D1A2E), Color(hex: 0x241C24), Color(hex: 0x2D2018)], startPoint: .top, endPoint: .bottom)
        : LinearGradient(colors: [Color(hex: 0xB9C8D3), Color(hex: 0xE6D6BE), Color(hex: 0xD2A981)], startPoint: .top, endPoint: .bottom)
    var rows: [[Face]] = []
    var row: [Face] = []
    for f in list {
        if f.width > 200 {
            if !row.isEmpty { rows.append(row); row = [] }
            rows.append([f])
        } else {
            row.append(f)
            if row.count == 2 { rows.append(row); row = [] }
        }
    }
    if !row.isEmpty { rows.append(row) }
    return VStack(spacing: 22) {
        ForEach(Array(rows.enumerated()), id: \.offset) { _, r in
            HStack(spacing: 22) {
                ForEach(Array(r.enumerated()), id: \.offset) { _, f in card(f, snap, scheme) }
            }
        }
    }
    .padding(26)
    .background(wallpaper)
}

@main
struct Render {
    @MainActor
    static func main() {
        let args = CommandLine.arguments
        let out = URL(fileURLWithPath: args.count > 1 ? args[1] : "widget-previews")
        let fonts = URL(fileURLWithPath: args.count > 2 ? args[2] : "ui/ios/App/SiddhaWidgets/Fonts")
        try? FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)
        for url in (try? FileManager.default.contentsOfDirectory(at: fonts, includingPropertiesForKeys: nil)) ?? []
        where url.pathExtension == "ttf" {
            CTFontManagerRegisterFontsForURL(url as CFURL, .process, nil)
        }

        let morning = Calendar.current.date(bySettingHour: 8, minute: 20, second: 0, of: Date()) ?? Date()
        let snap = Sample.snapshot(at: morning)
        let empty = Snapshot(now: morning)
        let phone = faces.filter { $0.name != "calendar-ipad" }

        for (scheme, theme) in [(ColorScheme.light, "light"), (.dark, "dark")] {
            for f in faces {
                write(card(f, snap, scheme), to: out.appendingPathComponent("\(f.name)-\(theme).png"))
            }
            write(sheet(snap, scheme, phone), to: out.appendingPathComponent("sheet-\(theme).png"))
            // Before the app has published anything: the words a new reader sees.
            write(sheet(empty, scheme, phone), to: out.appendingPathComponent("sheet-empty-\(theme).png"))
        }
    }
}
