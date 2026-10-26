import type { CapacitorConfig } from '@capacitor/cli';
import type { KeyboardResize } from '@capacitor/keyboard';

const config: CapacitorConfig = {
  appId: 'app.asksiddha.mobile',
  appName: 'Siddha',
  // Native bridge arguments can contain private chart/cache payloads. Keep
  // Capacitor's method-data logging disabled in debug and release builds.
  loggingBehavior: 'none',

  // Angular's production build output. Kept in step with angular.json's
  // outputPath — `npx cap sync` copies from here into the native projects,
  // so a stale path yields a native app running yesterday's bundle.
  webDir: '../frontend/dist/browser',

  server: {
    // Capacitor serves the bundle over https://localhost on both platforms
    // rather than the older capacitor:// and ionic:// schemes. This is the
    // origin the API must allow; see ALLOWED_ORIGINS in main.py.
    androidScheme: 'https',
    iosScheme: 'https',
  },

  // Angular consumes env(safe-area-inset-*); UIKit must not add a second inset.
  ios: { contentInset: 'never' },

  plugins: {
    CapacitorSQLite: {
      iosDatabaseLocation: 'Library/CapacitorDatabase',
      iosIsEncryption: true,
      iosKeychainPrefix: 'app.asksiddha.mobile',
      androidIsEncryption: true,
    },
    SplashScreen: {
      // Held until the web intro has painted: App calls SplashScreen.hide()
      // from afterNextRender (and again, as a safety net, when boot settles).
      // With auto-hide the native splash dropped after 500 ms whether or not
      // Angular had drawn anything, which could show a blank WebView between
      // the two.
      launchAutoHide: false,
      // The animated intro's backdrop (#100b06, app.scss
      // .animated-splash-overlay; android styles.xml NoActionBarLaunch), so
      // the hand-off from native to web splash is the same colour.
      backgroundColor: '#100B06',
      showSpinner: false,
      androidScaleType: 'CENTER_CROP',
    },
    Keyboard: {
      // iOS: resize the whole WebView above the keyboard, so the page gets
      // shorter instead of being covered. Android 15+ is handled by
      // Capacitor 8's SystemBars, which pads the WebView by the IME inset.
      // The accessory bar is hidden at runtime (NativeKeyboardService); the
      // plugin has no config key for it.
      resize: 'native' as KeyboardResize,
    },
    SocialLogin: {
      // Google and Apple use their own sign-in sheets (AuthService
      // signInWithGoogle / signInWithApple); Apple is called on iOS only.
      // Facebook off also keeps its SDK and the AD_ID permission out of the build.
      providers: { google: true, facebook: false, apple: true, twitter: false },
      logLevel: 1,
    },
    PushNotifications: {
      // Without this a push that lands while the app is open is delivered to
      // the listener but never shown, so the morning brief silently vanishes.
      presentationOptions: ['badge', 'sound', 'alert'],
    },
    StatusBar: {
      style: 'LIGHT',
      backgroundColor: '#FAF7F0',
    },
  },
};

export default config;
