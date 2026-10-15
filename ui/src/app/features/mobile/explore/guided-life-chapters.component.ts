import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { DashaPayload, DashaPeriod } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { GenericErrorComponent } from '../states/generic-error.component';

interface TimelineItem {
  title: string;
  detail: string;
  active?: boolean;
  future?: boolean;
}

interface CurrentChapter {
  lord: string;
  title: string;
  dates: string;
  progress: number;
  start: string;
  end: string;
}

interface ChapterInsight {
  tone: 'gold' | 'good' | 'accent';
  title: string;
  text: string;
}

@Component({
  selector: 'as-guided-life-chapters',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [GenericErrorComponent, RouterLink],
  templateUrl: './guided-life-chapters.component.html',
  styleUrl: './guided-life-chapters.component.scss',
})
export class GuidedLifeChaptersComponent {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);

  protected readonly dashas = signal<DashaPayload | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  /** Set when the store has no active profile; the screen then asks for birth details. */
  protected readonly noProfile = signal(false);

  /**
   * The running mahadasha from the engine, or null when the payload carries
   * none. Null renders an honest "no running chapter" state: this screen
   * used to invent a Saturn 2025-2028 chapter, with a progress bar and a
   * six-row timeline, for every person whose dasha had not loaded.
   */
  protected readonly current = computed<CurrentChapter | null>(() => {
    const dasha = this.dashas()?.current.mahadasha ?? this.dashas()?.mahadashas.find((row) => row.active) ?? null;
    if (!dasha) return null;
    const lord = dasha.lord;
    return {
      lord,
      title: `${lord}'s ${this.chapterMood(lord)} Phase`,
      dates: `${this.dateLabel(dasha.start)} · ${this.chapterLine(lord)}`,
      progress: this.progress(dasha),
      start: this.dateLabel(dasha.start),
      end: this.dateLabel(dasha.end),
    };
  });

  /** Lord-keyed guidance for the running chapter; nothing is shown without a lord. */
  protected readonly insights = computed<ChapterInsight[]>(() => {
    const lord = this.current()?.lord;
    return lord ? CHAPTER_INSIGHTS[lord] ?? [] : [];
  });

  protected readonly timeline = computed<TimelineItem[]>(() => {
    const periods = this.dashas()?.mahadashas;
    if (!periods?.length) return [];
    const activeIndex = Math.max(0, periods.findIndex((period) => period.active));
    return periods.slice(Math.max(0, activeIndex - 4), activeIndex + 2).map((period, index, rows) => ({
      title: `${period.lord} Chapter`,
      detail: `${this.dateLabel(period.start)}-${this.dateLabel(period.end)} · ${this.chapterLine(period.lord)}`,
      active: period.active,
      future: !period.active && index === rows.length - 1,
    }));
  });

  constructor() {
    effect(() => {
      const activeId = this.kundlis.activeId();
      void this.load(activeId);
    });
  }

  protected retry(): void {
    void this.load(this.kundlis.activeId());
  }

  private async load(expectedActiveId: string | null): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      const activeId = this.kundlis.activeId();
      if (expectedActiveId && activeId !== expectedActiveId) return;
      this.noProfile.set(!activeId);
      this.dashas.set(activeId ? await this.vedic.dashas(activeId) : null);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  private progress(period: DashaPeriod): number {
    const start = new Date(period.start).getTime();
    const end = new Date(period.end).getTime();
    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return 0;
    return Math.max(0, Math.min(100, ((Date.now() - start) / (end - start)) * 100));
  }

  private dateLabel(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value || '—';
    return date.getFullYear().toString();
  }

  private chapterMood(lord: string): string {
    return ({
      Saturn: 'Steady',
      Venus: 'Creative',
      Sun: 'Visible',
      Moon: 'Feeling',
      Mars: 'Active',
      Mercury: 'Learning',
      Jupiter: 'Expansive',
      Rahu: 'Changing',
      Ketu: 'Reflective',
    } as Record<string, string>)[lord] ?? 'Current';
  }

  private chapterLine(lord: string): string {
    return ({
      Saturn: 'Discipline, patience & foundations',
      Venus: 'Beauty, devotion & relationships',
      Sun: 'Identity, courage & right visibility',
      Moon: 'Emotional rhythm & inner listening',
      Mars: 'Drive, action & disciplined effort',
      Mercury: 'Communication, learning & adaptability',
      Jupiter: 'Growth, teachers & purpose',
      Rahu: 'Change, appetite & new territory',
      Ketu: 'Reflection, release & inner clarity',
    } as Record<string, string>)[lord] ?? 'A meaningful life chapter';
  }
}

/**
 * Three practical lines per dasha lord, framed as tendencies to work with.
 * They were previously one fixed Saturn-flavoured set shown under every
 * chapter, including a Venus or Rahu one.
 */
const CHAPTER_INSIGHTS: Record<string, ChapterInsight[]> = {
  Saturn: [
    { tone: 'gold', title: 'Work & Purpose', text: 'Give your effort a structure. Build foundations now; let recognition come later.' },
    { tone: 'good', title: 'Relationships', text: 'Choose patience over reaction. Existing bonds deepen through steadiness and shared responsibility.' },
    { tone: 'accent', title: 'Energy & Routine', text: 'Steady routines matter more than intensity. Prioritise consistency in sleep, food, and movement.' },
  ],
  Venus: [
    { tone: 'gold', title: 'Work & Purpose', text: 'Taste and agreement carry weight. Work that needs harmony, design or partnership tends to move.' },
    { tone: 'good', title: 'Relationships', text: 'Comfort and affection come forward. Keep generosity balanced so it stays a gift, not a debt.' },
    { tone: 'accent', title: 'Energy & Routine', text: 'Pleasure is easy to overdo. Keep beauty in the routine without letting the routine slip.' },
  ],
  Sun: [
    { tone: 'gold', title: 'Work & Purpose', text: 'Visibility and responsibility rise together. Take the lead where you can stand behind the result.' },
    { tone: 'good', title: 'Relationships', text: 'Pride can crowd out listening. Lead with warmth and leave room for others to be seen.' },
    { tone: 'accent', title: 'Energy & Routine', text: 'Mornings and daylight hours tend to carry you. Protect rest so confidence does not tip into strain.' },
  ],
  Moon: [
    { tone: 'gold', title: 'Work & Purpose', text: 'Mood shapes output. Plan around your rhythms rather than fighting them.' },
    { tone: 'good', title: 'Relationships', text: 'Family, home and belonging ask for attention. Small acts of care matter more than grand ones.' },
    { tone: 'accent', title: 'Energy & Routine', text: 'Sleep, water and quiet are the levers. Notice what the mind replays and give it a gentler script.' },
  ],
  Mars: [
    { tone: 'gold', title: 'Work & Purpose', text: 'Drive is available. Aim it at one finishable thing at a time instead of several fights at once.' },
    { tone: 'good', title: 'Relationships', text: 'Heat rises quickly. A pause before replying keeps courage from becoming conflict.' },
    { tone: 'accent', title: 'Energy & Routine', text: 'Movement is the outlet. Regular physical effort steadies the temper and sharpens focus.' },
  ],
  Mercury: [
    { tone: 'gold', title: 'Work & Purpose', text: 'Learning, writing, trade and negotiation tend to flow. Precision in detail pays off.' },
    { tone: 'good', title: 'Relationships', text: 'Conversation carries the bond. Say the thing clearly rather than hinting at it.' },
    { tone: 'accent', title: 'Energy & Routine', text: 'The mind runs fast. Build in offline stretches so curiosity does not turn into scatter.' },
  ],
  Jupiter: [
    { tone: 'gold', title: 'Work & Purpose', text: 'Growth favours the long view. Teachers, mentors and study open doors that effort alone does not.' },
    { tone: 'good', title: 'Relationships', text: 'Generosity and counsel come naturally. Offer guidance when asked and keep faith with your commitments.' },
    { tone: 'accent', title: 'Energy & Routine', text: 'Abundance can mean excess. Keep expansion in step with what the body and calendar can hold.' },
  ],
  Rahu: [
    { tone: 'gold', title: 'Work & Purpose', text: 'Ambition and unfamiliar territory pull strongly. Check the ground before committing to the leap.' },
    { tone: 'good', title: 'Relationships', text: 'New people and new appetites arrive. Keep your word tied to what you can actually deliver.' },
    { tone: 'accent', title: 'Energy & Routine', text: 'Restlessness is the signature. Anchor the days with a fixed rhythm so novelty stays a choice.' },
  ],
  Ketu: [
    { tone: 'gold', title: 'Work & Purpose', text: 'Outer reward matters less than inner clarity. Finish and release rather than start and accumulate.' },
    { tone: 'good', title: 'Relationships', text: 'Detachment can read as distance. Say what you are stepping back from so others are not left guessing.' },
    { tone: 'accent', title: 'Energy & Routine', text: 'Simplicity restores. Quiet practice, fewer inputs and clean routines keep the energy steady.' },
  ],
};
