import { TextKey } from './en';

/**
 * Telugu for the app's own words (audit I13). Empty on purpose until a
 * native speaker writes and checks each line: a missing key shows the
 * English, which is better than machine Telugu in a product about trust.
 * The UI language stays English (I18nService.UI_LANGUAGES) until this file
 * covers at least the shell and Today.
 */
export const TE: Partial<Record<TextKey, string>> = {};
