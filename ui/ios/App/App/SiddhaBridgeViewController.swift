import UIKit
import Capacitor

/// Main.storyboard's root view controller. Capacitor finds plugins that come
/// from npm packages on its own; the app's own plugins are registered here.
class SiddhaBridgeViewController: CAPBridgeViewController {

    override func capacitorDidLoad() {
        bridge?.registerPluginInstance(SiddhaWidgetsPlugin())
    }
}
