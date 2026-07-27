import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'app.astrospace.mobile',
  appName: 'AstroSpace',

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
};

export default config;
