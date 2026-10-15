import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'app.astrospace.mobile',
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
      iosKeychainPrefix: 'app.astrospace.mobile',
      androidIsEncryption: true,
    },
    SplashScreen: {
      // Matches the Siddha animated intro backdrop so the native launch bridge
      // does not flash a different color before Angular paints.
      backgroundColor: '#0A0E1F',
      showSpinner: false,
      androidScaleType: 'CENTER_CROP',
    },
    PushNotifications: {
      // Without this a push that lands while the app is open is delivered to
      // the listener but never shown, so the morning brief silently vanishes.
      presentationOptions: ['badge', 'sound', 'alert'],
    },
    StatusBar: {
      style: 'LIGHT',
      backgroundColor: '#F4F5FA',
    },
  },
};

export default config;
