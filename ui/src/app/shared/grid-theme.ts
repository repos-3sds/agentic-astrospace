import { AllCommunityModule, ModuleRegistry, themeQuartz } from 'ag-grid-community';

ModuleRegistry.registerModules([AllCommunityModule]);

/** AG Grid Quartz theme bound to the AstroSpace tokens. */
export const darkGridTheme = themeQuartz.withParams({
  backgroundColor: '#1d1712',
  foregroundColor: '#f3eadc',
  headerBackgroundColor: '#261f18',
  headerTextColor: '#b2a592',
  borderColor: '#3a3026',
  rowHoverColor: 'rgba(224, 100, 79, 0.08)',
  accentColor: '#e0644f',
  fontFamily: "'Inter', system-ui, sans-serif",
  fontSize: 13,
  headerFontWeight: 600,
  wrapperBorderRadius: 8,
  rowVerticalPaddingScale: 1.2,
});

export const lightGridTheme = themeQuartz.withParams({
  backgroundColor: '#ffffff',
  foregroundColor: '#201a14',
  headerBackgroundColor: '#faf7f0',
  headerTextColor: '#756b5e',
  borderColor: '#e7ddd0',
  rowHoverColor: 'rgba(177, 63, 46, 0.06)',
  accentColor: '#b13f2e',
  fontFamily: "'Inter', system-ui, sans-serif",
  fontSize: 13,
  headerFontWeight: 600,
  wrapperBorderRadius: 8,
  rowVerticalPaddingScale: 1.2,
});
