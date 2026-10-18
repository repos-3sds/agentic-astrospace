import { ChangeDetectionStrategy, Component, inject, input, signal } from '@angular/core';
import { Share } from '@capacitor/share';
import { Capacitor } from '@capacitor/core';

import { HapticsService } from '../../../core/haptics.service';
import { shareFile } from '../../../core/native-share';
import { Subhashita, SUBHASHITA_TITLE } from '../../../core/subhashita.service';
import { longDate, shareText, storyCardFile } from './story-card';

/**
 * A verse as it will be shared: the card is a small copy of the 9:16 status
 * image (story-card.ts), so what the reader sees is what their friends get.
 * Used by the Subhashita screen and by the sheet shown on the day's first open.
 */
@Component({
  selector: 'as-subhashita-verse',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @let v = verse();
    <figure class="card">
      <span class="brand siddha-brand" aria-hidden="true">Siddha</span>
      <figcaption class="eyebrow">{{ title }} · {{ date(v.date) }}</figcaption>
      <p class="sanskrit" lang="sa">{{ v.sanskrit }}</p>
      <blockquote class="english">{{ v.english }}</blockquote>
      @if (v.meaning) {
        <p class="meaning">{{ v.meaning }}</p>
      }
      <p class="source">— {{ v.source }} {{ v.ref }}</p>
    </figure>

    <div class="actions">
      <button class="share" type="button" [disabled]="busy()" (click)="shareImage()">
        {{ busy() ? 'Preparing…' : 'Share to status' }}
      </button>
      <button class="words" type="button" [disabled]="busy()" (click)="shareWords()">Share the words</button>
    </div>
    @if (error()) {
      <p class="error" role="alert">{{ error() }}</p>
    }
  `,
  styleUrl: './subhashita-verse.component.scss',
})
export class SubhashitaVerseComponent {
  private readonly haptics = inject(HapticsService);

  readonly verse = input.required<Subhashita>();
  protected readonly title = SUBHASHITA_TITLE;
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly date = longDate;

  /** The 9:16 picture, for a WhatsApp or Instagram status. */
  protected async shareImage(): Promise<void> {
    this.haptics.tap();
    this.busy.set(true);
    this.error.set(null);
    try {
      const file = await storyCardFile(this.verse());
      const shared = await shareFile(file, { title: SUBHASHITA_TITLE });
      if (!shared) download(file);
    } catch (err) {
      this.error.set(err instanceof Error ? err.message : 'The image could not be shared.');
    } finally {
      this.busy.set(false);
    }
  }

  protected async shareWords(): Promise<void> {
    this.haptics.tap();
    this.error.set(null);
    const text = shareText(this.verse());
    try {
      if (Capacitor.isNativePlatform()) {
        await Share.share({ title: SUBHASHITA_TITLE, text });
      } else if (navigator.share) {
        await navigator.share({ title: SUBHASHITA_TITLE, text });
      } else {
        await navigator.clipboard.writeText(text);
        this.error.set('Copied. Paste it wherever you like.');
      }
    } catch (err) {
      const message = String((err as Error)?.message ?? '').toLowerCase();
      if ((err as DOMException)?.name !== 'AbortError' && !message.includes('cancel')) {
        this.error.set('The words could not be shared.');
      }
    }
  }
}

function download(file: File): void {
  const url = URL.createObjectURL(file);
  const link = document.createElement('a');
  link.href = url;
  link.download = file.name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
