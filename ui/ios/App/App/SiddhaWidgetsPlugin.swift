import Foundation
import Capacitor
import WidgetKit

/// The app's side of the home-screen widgets, the iOS twin of
/// ui/android/.../widgets/WidgetsPlugin.java. The app publishes what each
/// widget shows as a JSON "part" (today, calendar, subhashita, mantra) into
/// the App Group (Shared/WidgetGroup.swift); the widget extension
/// (SiddhaWidgets/) draws from those parts without the app running. A widget
/// tap that opens a screen comes back as an "open" event with the route.
///
/// Registered by SiddhaBridgeViewController: app-local plugins are not found
/// by Capacitor's package scan.
@objc(SiddhaWidgetsPlugin)
public class SiddhaWidgetsPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "SiddhaWidgetsPlugin"
    public let jsName = "SiddhaWidgets"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "publish", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "saveListenAudio", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "takeMantraTaps", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "clear", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "getOpacity", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "setOpacity", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "takePendingRoute", returnType: CAPPluginReturnPromise),
    ]

    private static weak var instance: SiddhaWidgetsPlugin?
    /// A route a widget asked for before the web layer was listening.
    private static var pendingRoute: String?

    override public func load() {
        Self.instance = self
    }

    @objc func publish(_ call: CAPPluginCall) {
        guard let part = call.getString("part"), let data = call.getObject("data") else {
            call.reject("part and data are required")
            return
        }
        guard JSONSerialization.isValidJSONObject(data),
              let json = try? JSONSerialization.data(withJSONObject: data),
              let text = String(data: json, encoding: .utf8) else {
            call.reject("data is not JSON")
            return
        }
        WidgetGroup.put(part, json: text)
        Self.reloadWidgets()
        call.resolve()
    }

    /// Android keeps Siddha's natural voice for its Listen widget. On iPhone
    /// the Listen widget opens the app's Listen sheet, which plays it, so
    /// there is nothing to keep here yet.
    @objc func saveListenAudio(_ call: CAPPluginCall) {
        call.resolve()
    }

    @objc func takeMantraTaps(_ call: CAPPluginCall) {
        let taps = WidgetGroup.takeMantraTaps()
        call.resolve([
            "key": taps["key"] as? String ?? "",
            "date": taps["date"] as? String ?? "",
            "taps": taps["taps"] as? Int ?? 0,
        ])
    }

    @objc func clear(_ call: CAPPluginCall) {
        WidgetGroup.clear()
        Self.reloadWidgets()
        call.resolve()
    }

    /// How solid the widget cards are, 0 to 100; kept through sign-out.
    @objc func getOpacity(_ call: CAPPluginCall) {
        call.resolve(["percent": WidgetGroup.opacity])
    }

    @objc func setOpacity(_ call: CAPPluginCall) {
        guard let percent = call.getInt("percent") else {
            call.reject("percent is required")
            return
        }
        WidgetGroup.opacity = percent
        Self.reloadWidgets()
        call.resolve()
    }

    /// The route a widget opened the app with, if the event was missed.
    @objc func takePendingRoute(_ call: CAPPluginCall) {
        call.resolve(["route": Self.pendingRoute ?? ""])
        Self.pendingRoute = nil
    }

    /// Called by SceneDelegate for every URL; true when it came from a widget.
    static func handle(url: URL) -> Bool {
        guard url.scheme == WidgetGroup.scheme, url.host == WidgetGroup.host else { return false }
        guard let route = WidgetGroup.route(from: url) else { return true }
        guard let plugin = instance else {
            pendingRoute = route
            return true
        }
        // Retained until the web layer adds its listener, so a cold start
        // from a widget still lands on the screen it asked for.
        plugin.notifyListeners("open", data: ["route": route], retainUntilConsumed: true)
        return true
    }

    private static func reloadWidgets() {
        WidgetCenter.shared.reloadAllTimelines()
    }
}
