import UIKit
import Capacitor

// iOS 27 stops an app at launch that has not adopted the scene lifecycle
// (UIApplicationEvaluateRuntimeIssueForNoSceneLifecycleAdoption): TestFlight
// build 587 crashed within 160 ms on every iOS 27 iPhone. Info.plist's
// UIApplicationSceneManifest names this class and the Main storyboard, so
// UIKit builds the window and CAPBridgeViewController here instead of in the
// app delegate.
//
// With a scene, UIKit no longer calls the app delegate's open-URL and
// user-activity methods; they arrive here and go to Capacitor's proxy, which
// the App plugin turns into appUrlOpen (the sign-in callback).
class SceneDelegate: UIResponder, UIWindowSceneDelegate {

    var window: UIWindow?

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        // Let the WebView paint behind the status bar. The Angular mobile shell
        // consumes env(safe-area-inset-top), so UIKit applying its own inset
        // leaves an unpainted white strip above dark-mode screens.
        DispatchQueue.main.async { [weak self] in
            guard let bridge = self?.window?.rootViewController as? CAPBridgeViewController else {
                return
            }
            bridge.webView?.scrollView.contentInsetAdjustmentBehavior = .never
        }

        // A cold start from a link or a handed-off activity carries it here
        // rather than in a later callback.
        if !connectionOptions.urlContexts.isEmpty {
            self.scene(scene, openURLContexts: connectionOptions.urlContexts)
        }
        for activity in connectionOptions.userActivities {
            self.scene(scene, continue: activity)
        }
    }

    func scene(_ scene: UIScene, openURLContexts URLContexts: Set<UIOpenURLContext>) {
        for context in URLContexts {
            // A widget tap goes to the widgets plugin, not to the web layer's
            // link handling (SiddhaWidgetsPlugin.handle).
            if SiddhaWidgetsPlugin.handle(url: context.url) { continue }
            var options: [UIApplication.OpenURLOptionsKey: Any] = [:]
            options[.sourceApplication] = context.options.sourceApplication
            options[.annotation] = context.options.annotation
            options[.openInPlace] = context.options.openInPlace
            _ = ApplicationDelegateProxy.shared.application(UIApplication.shared, open: context.url, options: options)
        }
    }

    func scene(_ scene: UIScene, continue userActivity: NSUserActivity) {
        _ = ApplicationDelegateProxy.shared.application(UIApplication.shared, continue: userActivity, restorationHandler: { _ in })
    }
}
