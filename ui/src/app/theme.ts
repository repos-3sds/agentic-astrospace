import { definePreset } from '@primeuix/themes';
import Aura from '@primeuix/themes/aura';

/**
 * AstroSpace preset: refined warm neutral in light mode, ink/copper in dark mode.
 */
export const CelestialPreset = definePreset(Aura, {
  semantic: {
    primary: {
      50: '#fff1ed',
      100: '#ffe1d8',
      200: '#ffc5b6',
      300: '#ff9d87',
      400: '#f4745d',
      500: '#e0644f',
      600: '#c94835',
      700: '#b13f2e',
      800: '#8f2f22',
      900: '#762d23',
      950: '#43140d',
    },
    colorScheme: {
      light: {
        surface: {
          0: '#ffffff',
          50: '#faf7f0',
          100: '#f2ece2',
          200: '#e7ddd0',
          300: '#d5c6b4',
          400: '#aa9983',
          500: '#887655',
          600: '#67583e',
          700: '#4c3f2d',
          800: '#342a1d',
          900: '#201a14',
          950: '#120d09',
        },
      },
      dark: {
        surface: {
          0: '#ffffff',
          50: '#f3eadc',
          100: '#e5d5bd',
          200: '#cdb991',
          300: '#ac9363',
          400: '#8a7049',
          500: '#6b5638',
          600: '#514333',
          700: '#3a3026',
          800: '#261f18',
          900: '#1d1712',
          950: '#15110d',
        },
      },
    },
  },
});
