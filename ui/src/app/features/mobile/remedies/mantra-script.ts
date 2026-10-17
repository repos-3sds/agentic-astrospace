import { Injectable, inject, signal } from '@angular/core';
import { PreferencesService } from '../../../core/preferences.service';
import { MantraText, RemedyRecommendationPractice } from '../../../core/vedic.service';

/** The script a mantra is shown in. The text, not a translation of it. */
export type MantraScript = 'te' | 'en' | 'sa';

export const MANTRA_SCRIPTS: { id: MantraScript; label: string }[] = [
  { id: 'te', label: 'తెలుగు' },
  { id: 'en', label: 'English' },
  { id: 'sa', label: 'संस्कृत' },
];

const STORAGE_KEY = 'siddha.mantraScript:v1';

/**
 * One choice of script, shared by the Remedies page and the tracker. It
 * starts from the reader's answer language (Telugu readers see Telugu script)
 * and remembers a change per device.
 */
@Injectable({ providedIn: 'root' })
export class MantraScriptService {
  private readonly preferences = inject(PreferencesService);
  readonly script = signal<MantraScript>(this.initial());

  set(script: MantraScript): void {
    this.script.set(script);
    try {
      localStorage.setItem(STORAGE_KEY, script);
    } catch {
      // Storage can be unavailable; the choice still holds for this visit.
    }
  }

  text(practice: RemedyRecommendationPractice | null): string | null {
    const text: MantraText | undefined = practice?.text;
    if (!text) return null;
    return text[this.script()] || text.en;
  }

  /** The meaning in the reader's language: Telugu with Telugu script, Hindi with Devanagari. */
  meaning(practice: RemedyRecommendationPractice | null): string | null {
    const meaning = practice?.meaning;
    if (!meaning) return null;
    const script = this.script();
    if (script === 'te') return meaning.te || meaning.en;
    if (script === 'sa') return meaning.hi || meaning.en;
    return meaning.en;
  }

  private initial(): MantraScript {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'te' || stored === 'en' || stored === 'sa') return stored;
    } catch {
      // Fall through to the language default.
    }
    return this.preferences.language() === 'te' ? 'te' : 'en';
  }
}
