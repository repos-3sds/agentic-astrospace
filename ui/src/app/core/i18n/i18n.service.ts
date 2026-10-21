import { Injectable, Pipe, PipeTransform, computed, inject, signal } from '@angular/core';
import { EN, TextKey } from './en';
import { TE } from './te';

export type UiLanguage = 'en' | 'te';

const TABLES: Record<UiLanguage, Partial<Record<TextKey, string>>> = { en: EN, te: TE };

/**
 * The app's own words in the reader's UI language (audit I13).
 *
 * Separate from the Ask answer language in Settings (PreferencesService
 * .language), which already switches Ask and the brief to Telugu: the UI
 * itself stays English until te.ts is written and checked by a native
 * speaker, so `UI_LANGUAGES` lists English alone and `use('te')` is
 * refused. Signals, not a library: the shell and a few screens need a
 * lookup, not plurals or ICU formats yet, and nothing here needs a new
 * dependency to be swapped for Transloco later.
 */
@Injectable({ providedIn: 'root' })
export class I18nService {
  static readonly UI_LANGUAGES: readonly UiLanguage[] = ['en'];

  private readonly language = signal<UiLanguage>('en');
  readonly current = this.language.asReadonly();
  private readonly table = computed(() => TABLES[this.language()]);

  use(language: UiLanguage): boolean {
    if (!I18nService.UI_LANGUAGES.includes(language)) return false;
    this.language.set(language);
    return true;
  }

  /** The phrase in the UI language, else English. */
  t(key: TextKey): string {
    return this.table()[key] ?? EN[key];
  }
}

/** `{{ 'tab.today' | t }}`; impure so a language switch repaints. */
@Pipe({ name: 't', standalone: true, pure: false })
export class TranslatePipe implements PipeTransform {
  private readonly i18n = inject(I18nService);

  transform(key: TextKey): string {
    return this.i18n.t(key);
  }
}
