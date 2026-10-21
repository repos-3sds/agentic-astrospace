/**
 * The app's own words, in English: the source every other language is
 * translated from (audit I13). Start of the move: the shell's tab bar and
 * offline banner. Screens move their fixed labels here as they are touched;
 * text that comes from the server (readings, festival names, Ask answers)
 * is not app text and is translated, if at all, on the server.
 *
 * Keys are `area.thing`. Keep each value a whole phrase: word order differs
 * between English and Telugu, so never build a sentence from two keys.
 */
export const EN = {
  'tab.today': 'Today',
  'tab.ask': 'Ask',
  'tab.calendar': 'Calendar',
  'tab.explore': 'Explore',
  'tab.settings': 'Settings',
  'tab.yantra': 'Yantra',
  'tab.dashas': 'Dashas',
  'network.offline': 'You’re offline',
  'network.offline_detail': 'Saved guidance stays available.',
  'network.reconnecting': 'Reconnecting',
  'network.reconnecting_detail': 'Checking the connection…',
  'network.retry': 'Retry',
} as const;

export type TextKey = keyof typeof EN;
