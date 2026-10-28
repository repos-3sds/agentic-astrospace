import Foundation

/// What the app and the widget extension share: the App Group's defaults,
/// where the app writes one JSON "part" per subject (today, calendar,
/// subhashita, mantra) and the widgets only read. It is the iOS twin of
/// ui/android/.../widgets/WidgetStore.java, with the same part names and
/// field names, so ui/src/app/core/widget-bridge.service.ts publishes once
/// for both. Nothing here touches the network.
///
/// Compiled into both targets (App and SiddhaWidgets).
enum WidgetGroup {

    /// Registered on both App IDs in Apple Developer; the entitlements files
    /// name it too.
    static let id = "group.app.asksiddha.mobile"

    /// Widget taps open `app.asksiddha.mobile://widget?route=/m/today`. The
    /// scheme is the app's own (Info.plist), and SceneDelegate hands these to
    /// SiddhaWidgetsPlugin before anything else sees them.
    static let scheme = "app.asksiddha.mobile"
    static let host = "widget"

    private static let partPrefix = "part."
    private static let mantraTapsKey = "mantra.taps"
    /// Kept apart from the parts so signing out does not reset it.
    private static let opacityKey = "look.opacity"

    static var defaults: UserDefaults {
        UserDefaults(suiteName: id) ?? .standard
    }

    // MARK: Parts

    static func put(_ part: String, json: String) {
        defaults.set(json, forKey: partPrefix + part)
    }

    /// The part as last published, or nil when the app has not sent it yet.
    static func data(_ part: String) -> Data? {
        defaults.string(forKey: partPrefix + part)?.data(using: .utf8)
    }

    static func object(_ part: String) -> [String: Any]? {
        guard let data = data(part) else { return nil }
        return (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
    }

    /// Signing out must not leave the last account's day on the home screen.
    static func clear() {
        let store = defaults
        for key in store.dictionaryRepresentation().keys where key.hasPrefix(partPrefix) || key == mantraTapsKey {
            store.removeObject(forKey: key)
        }
    }

    // MARK: Look

    /// How solid the widget cards are, 0 (clear) to 100 (solid, the default).
    static var opacity: Int {
        get { defaults.object(forKey: opacityKey) == nil ? 100 : defaults.integer(forKey: opacityKey) }
        set { defaults.set(max(0, min(100, newValue)), forKey: opacityKey) }
    }

    // MARK: Mantra taps made on the widget, waiting for the app to fold them in

    /// Counts one tap for the practice and day; returns the new pending total.
    @discardableResult
    static func addMantraTap(key: String, date: String) -> Int {
        let taps = pendingTaps()
        var count = 1
        if taps["key"] as? String == key, taps["date"] as? String == date {
            count = (taps["taps"] as? Int ?? 0) + 1
        }
        let next: [String: Any] = ["key": key, "date": date, "taps": count]
        if let data = try? JSONSerialization.data(withJSONObject: next), let text = String(data: data, encoding: .utf8) {
            defaults.set(text, forKey: mantraTapsKey)
        }
        return count
    }

    /// Hands the pending taps to the app and forgets them.
    static func takeMantraTaps() -> [String: Any] {
        let taps = pendingTaps()
        defaults.removeObject(forKey: mantraTapsKey)
        return taps
    }

    private static func pendingTaps() -> [String: Any] {
        guard let raw = defaults.string(forKey: mantraTapsKey), let data = raw.data(using: .utf8) else { return [:] }
        return ((try? JSONSerialization.jsonObject(with: data)) as? [String: Any]) ?? [:]
    }

    // MARK: Days and links

    /// The phone's own calendar day, the same YYYY-MM-DD the app uses.
    static func isoDay(_ date: Date = Date()) -> String {
        let parts = Calendar.current.dateComponents([.year, .month, .day], from: date)
        return String(format: "%04d-%02d-%02d", parts.year ?? 0, parts.month ?? 0, parts.day ?? 0)
    }

    static func url(_ route: String) -> URL {
        var components = URLComponents()
        components.scheme = scheme
        components.host = host
        components.queryItems = [URLQueryItem(name: "route", value: route)]
        return components.url ?? URL(string: "\(scheme)://\(host)")!
    }

    /// The in-app route a widget link asks for, or nil when the URL is not one.
    static func route(from url: URL) -> String? {
        guard url.scheme == scheme, url.host == host,
              let route = URLComponents(url: url, resolvingAgainstBaseURL: false)?
                .queryItems?.first(where: { $0.name == "route" })?.value,
              route.hasPrefix("/m/") else { return nil }
        return route
    }
}
