import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { KundliStore } from '../../../core/kundli.store';
import {
  RemedyRecommendationGroup,
  RemedyRecommendationPractice,
  VedicService,
} from '../../../core/vedic.service';
import { HapticsService } from '../../../core/haptics.service';
import { MobileTtsService } from '../../../core/mobile-tts.service';
import { NaturalVoiceService } from '../../../core/natural-voice.service';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { SelectHapticDirective } from '../shared/select-haptic.directive';
import { MANTRA_SCRIPTS, MantraScriptService } from './mantra-script';

/**
 * Remedy detail — mantra tracker (Figma node 29:109).
 *
 * The count ring is data, not decoration: it redraws on every tap, so — like
 * the day gauge (13:20) — it is a stroked circle rather than the pasted export.
 * The geometry is lifted from the export so it lines up exactly:
 *
 *   outer radius 110, band 15.4 wide  ->  stroke-width 15.4, centre r 102.3
 *   track #e6dccd (--m-border), arc #b13f2e (--m-accent)
 *
 * The two exported ellipses are the only assets deliberately not used verbatim.
 *
 * On the counting itself: the target is a traditional count (108), and the
 * screen says "traditional practice" in the eyebrow and again above the fold.
 * The streak is there to help someone keep a practice they chose, which is why
 * nothing here warns about breaking it — a lapsed streak is not a consequence,
 * and dressing it as one would turn a practice into a debt.
 */
@Component({
  selector: 'as-mantra-tracker',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackLinkDirective, RouterLink, SelectHapticDirective],
  templateUrl: './mantra-tracker.component.html',
  styleUrl: './mantra-tracker.component.scss',
})
export class MantraTrackerComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  private readonly haptics = inject(HapticsService);
  private readonly naturalVoice = inject(NaturalVoiceService);
  private readonly nativeTts = inject(MobileTtsService);
  protected readonly scripts = inject(MantraScriptService);
  protected readonly scriptOptions = MANTRA_SCRIPTS;
  private readonly params = toSignal(this.route.queryParamMap, { requireSync: true });

  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly group = signal<RemedyRecommendationGroup | null>(null);
  protected readonly practice = signal<RemedyRecommendationPractice | null>(null);
  protected readonly count = signal(0);
  protected readonly completedDates = signal<string[]>([]);
  protected readonly mode = signal<'manual' | 'auto'>('manual');
  protected readonly listen = signal<'idle' | 'loading' | 'playing'>('idle');
  /** How far through the mantra the voice is, 0 to 1, for the follow-along highlight. */
  protected readonly progress = signal(0);
  private player: HTMLAudioElement | null = null;
  private frame: number | null = null;
  /** Bumped on every start and stop, so a slow load can't start after Stop. */
  private listenRun = 0;

  protected readonly eyebrow = computed(() => {
    const trigger = this.group()?.trigger;
    if (!trigger) return 'TRADITIONAL PRACTICE';
    const group = this.group();
    if (group?.slot === 'period' && trigger.mahadasha) return `${trigger.mahadasha}–${trigger.planet} period · traditional practice`.toUpperCase();
    if (group?.slot === 'life_area' && group.domain_label) return `${group.domain_label} · traditional practice`.toUpperCase();
    if (trigger.kind === 'dasha') return `${trigger.planet ?? 'Planet'} ${trigger.level ?? 'dasha'} · traditional practice`.toUpperCase();
    return `${trigger.kind} · traditional practice`.toUpperCase();
  });
  protected readonly practiceTitle = computed(() => this.practice()?.title ?? 'Selected practice');
  protected readonly practiceTextLabel = computed(() => this.practice()?.type === 'mantra' ? 'MANTRA' : 'PRACTICE TEXT');
  protected readonly literalPracticeText = computed(() => {
    const practice = this.practice();
    if (!practice) return '';
    if (practice.type !== 'mantra') return this.devotionalFallback(practice);
    const text = this.scripts.text(practice);
    if (text) return text;
    const audio = this.practice()?.audio;
    return audio?.text || audio?.transliteration || practice.title;
  });
  /**
   * The on-screen mantra as words, each with where it ends as a share of the
   * text. The voice reads Telugu while the screen may show another script, so
   * the highlight follows position in the text rather than exact word timing.
   */
  protected readonly lyricWords = computed(() => {
    const words = this.literalPracticeText().split(/\s+/).filter(Boolean);
    const total = words.reduce((sum, w) => sum + w.length, 0) || 1;
    let seen = 0;
    return words.map((text) => {
      const start = seen / total;
      seen += text.length;
      return { text, start };
    });
  });
  protected readonly activeWord = computed(() => {
    const p = this.progress();
    const words = this.lyricWords();
    let index = 0;
    for (let i = 0; i < words.length; i++) if (words[i].start <= p) index = i;
    return index;
  });
  protected readonly hasScripts = computed(() => !!this.practice()?.text);
  protected readonly meaning = computed(() => this.scripts.meaning(this.practice()));
  protected readonly target = computed(() => this.practice()?.target_count ?? (this.practice()?.type === 'deity' ? 1 : 108));
  protected readonly audioPending = computed(() => this.practice()?.audio?.source_status === 'pending_assets' || !this.practice()?.audio?.audio_url);

  protected readonly streakLabel = computed(() => {
    const days = this.completedDates().length;
    return days ? `${days}-day practice history` : 'Start this practice today';
  });

  // Ring geometry, from the 220px export.
  protected readonly SIZE = 220;
  protected readonly C = 110;
  protected readonly R = 102.3;
  protected readonly STROKE = 15.4;
  protected readonly CIRCUMFERENCE = 2 * Math.PI * 102.3;

  protected readonly dashOffset = computed(() => {
    const target = this.target();
    const fraction = target > 0 ? this.count() / target : 0;
    return this.CIRCUMFERENCE * (1 - Math.min(1, Math.max(0, fraction)));
  });

  constructor() {
    void this.load();
    inject(DestroyRef).onDestroy(() => this.stopListening());
  }

  /**
   * Reads the mantra aloud once. The recorded track wins when there is one;
   * otherwise Siddha's natural voice (Plus), otherwise the phone's own voice.
   * It reads the Telugu script whatever script is on screen: both voices say
   * Telugu letters as written, while the romanised form gets read as English.
   */
  protected async toggleListen(): Promise<void> {
    if (this.listen() !== 'idle') {
      this.stopListening();
      return;
    }
    const practice = this.practice();
    if (!practice) return;
    this.haptics.tap();
    const run = ++this.listenRun;
    this.listen.set('loading');
    const telugu = practice.text?.te?.trim();
    const text = telugu || this.literalPracticeText();
    try {
      let url = practice.audio?.audio_url ?? null;
      if (!url && await this.naturalVoice.available()) {
        url = await this.naturalVoice.audioUrl(text).catch(() => null);
      }
      if (run !== this.listenRun) return;
      if (url) {
        const player = new Audio(url);
        this.player = player;
        player.onended = () => this.finishListening(run);
        player.onerror = () => this.finishListening(run);
        await player.play();
        this.listen.set('playing');
        this.follow(run, () => player.duration > 0 ? player.currentTime / player.duration : 0);
        return;
      }
      this.listen.set('playing');
      // Phone voices don't report their position, so pace the highlight by
      // an estimate of the reading time at rate 0.8 and hold just short of
      // the end until the voice actually finishes.
      const started = performance.now();
      const estimateMs = Math.max(2500, text.length * 110);
      this.follow(run, () => Math.min(0.97, (performance.now() - started) / estimateMs));
      await this.speakOnPhone(text, telugu ? 'te-IN' : 'en-IN');
      this.finishListening(run);
    } catch {
      this.finishListening(run);
    }
  }

  private async speakOnPhone(text: string, lang: string): Promise<void> {
    if (this.nativeTts.nativeAvailable()) {
      await this.nativeTts.speak(text, { lang, rate: 0.8, pitch: 1 });
      return;
    }
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
    await new Promise<void>((resolve) => {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang;
      utterance.rate = 0.8;
      utterance.onend = () => resolve();
      utterance.onerror = () => resolve();
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
    });
  }

  private follow(run: number, position: () => number): void {
    const tick = () => {
      if (run !== this.listenRun) return;
      this.progress.set(position());
      this.frame = requestAnimationFrame(tick);
    };
    tick();
  }

  private finishListening(run: number): void {
    if (run !== this.listenRun) return;
    this.endFollow();
    this.player = null;
    this.listen.set('idle');
  }

  private endFollow(): void {
    if (this.frame !== null) cancelAnimationFrame(this.frame);
    this.frame = null;
    this.progress.set(0);
  }

  private stopListening(): void {
    this.listenRun++;
    this.endFollow();
    this.player?.pause();
    this.player = null;
    void this.nativeTts.stop().catch(() => undefined);
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) window.speechSynthesis.cancel();
    this.listen.set('idle');
  }

  /** Counts up to the target and stops. Past 108 the count means nothing. */
  protected tap(): void {
    this.haptics.tap();
    this.count.update((n) => {
      const next = Math.min(this.target(), n + 1);
      if (next >= this.target()) {
        this.completeToday();
      } else {
        this.persist(next, this.completedDates());
      }
      return next;
    });
  }

  protected readonly done = computed(() => this.count() >= this.target());

  /** Takes back one count, for a double tap. Undoing the last one reopens today. */
  protected undo(): void {
    const next = Math.max(0, this.count() - 1);
    if (next === this.count()) return;
    this.haptics.tap();
    const dates = this.withoutToday();
    this.completedDates.set(dates);
    this.count.set(next);
    this.persist(next, dates);
  }

  protected resetToday(): void {
    const dates = this.withoutToday();
    this.completedDates.set(dates);
    this.count.set(0);
    this.persist(0, dates);
  }

  private withoutToday(): string[] {
    const today = this.todayKey();
    return this.completedDates().filter((d) => d !== today);
  }

  /** The bottom Completed button: for someone who counted on a mala instead. */
  protected markCompleted(): void {
    if (this.done()) return;
    this.count.set(this.target());
    this.completeToday();
  }

  protected completeToday(): void {
    const today = this.todayKey();
    const dates = this.completedDates().includes(today)
      ? this.completedDates()
      : [...this.completedDates(), today];
    this.completedDates.set(dates);
    this.persist(this.target(), dates);
    this.haptics.success();
  }

  protected audioNote(): string {
    return this.practice()?.audio?.note ?? 'Recorded audio is not available yet. Manual counting is ready.';
  }

  protected practiceContext(): string {
    const practice = this.practice();
    const group = this.group();
    const pieces = [
      practice?.type === 'mantra' ? `${practice.target_count ?? 108}-count mantra` : 'Prayer practice',
      practice?.preferred_day,
      practice?.planet,
      group?.reason_short,
    ].filter(Boolean);
    return pieces.join(' · ');
  }

  protected reminderLabel(): string {
    const practice = this.practice();
    if (!practice) return 'Set practice reminder';
    const day = practice.preferred_day || 'practice';
    return practice.type === 'mantra' ? `Set ${day} mantra reminder` : `Set ${day} prayer reminder`;
  }

  private async load(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      const activeId = this.kundlis.activeId();
      if (!activeId) throw new Error('Select a profile before opening a practice.');
      const recommendationId = this.params().get('recommendation');
      const practiceSlug = this.params().get('practice');
      if (!recommendationId || !practiceSlug) throw new Error('Practice selection is missing.');
      const payload = await this.vedic.remedyPlan(activeId);
      const group = payload.groups.find((row) => row.recommendation_id === recommendationId) ?? null;
      const practice = group?.practices.find((row) => row.practice_slug === practiceSlug) ?? null;
      if (!group || !practice) throw new Error('This practice is no longer active for the selected profile.');
      this.group.set(group);
      this.practice.set(practice);
      this.restore(activeId, recommendationId, practiceSlug);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  private storageKey(): string | null {
    const activeId = this.kundlis.activeId();
    const recommendationId = this.params().get('recommendation');
    const practiceSlug = this.params().get('practice');
    if (!activeId || !recommendationId || !practiceSlug) return null;
    return `siddha.remedyPractice:v1:${activeId}:${recommendationId}:${practiceSlug}`;
  }

  private restore(activeId: string, recommendationId: string, practiceSlug: string): void {
    const key = `siddha.remedyPractice:v1:${activeId}:${recommendationId}:${practiceSlug}`;
    try {
      const stored = JSON.parse(localStorage.getItem(key) || 'null') as { count?: number; completedDates?: string[] } | null;
      this.count.set(Math.min(this.target(), Math.max(0, stored?.count ?? 0)));
      this.completedDates.set(Array.isArray(stored?.completedDates) ? stored.completedDates : []);
    } catch {
      this.count.set(0);
      this.completedDates.set([]);
    }
  }

  private persist(count: number, completedDates: string[]): void {
    const key = this.storageKey();
    if (!key) return;
    localStorage.setItem(key, JSON.stringify({
      count,
      completedDates,
      updatedAt: new Date().toISOString(),
    }));
  }

  private todayKey(): string {
    return new Date().toISOString().slice(0, 10);
  }

  private devotionalFallback(practice: RemedyRecommendationPractice): string {
    if (practice.type !== 'deity') return practice.instructions;
    const deity = practice.title.replace(/^Prayer to\s+/i, '').trim();
    return deity ? `Offer a simple prayer to ${deity}. Sit quietly, state your intention, and close with gratitude.` : practice.instructions;
  }
}
