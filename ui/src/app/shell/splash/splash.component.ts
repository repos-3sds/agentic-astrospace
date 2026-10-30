import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  ViewChild,
  inject,
} from '@angular/core';
import { drawGalaxy } from './galaxy-draw';

@Component({
  selector: 'app-splash',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="splash" [class.dark]="dark" [class.mark-only]="markOnly" aria-label="Siddha loading">
      <div class="galaxy-mark" role="img" aria-label="Siddha galaxy mark">
        <div class="halo"></div>
        <div class="tilt"><canvas #galaxy class="galaxy" width="720" height="720"></canvas></div>
        <div class="glow"></div>
      </div>

      @if (!markOnly) {
        <div class="copy">
          <h1 class="siddha-wordmark">{{ appName }}</h1>
          <p>{{ tagline }}</p>
        </div>
      }
    </section>
  `,
  styles: [
    `
      :host {
        width: 100%;
        height: 100%;
        display: block;
      }

      .splash {
        width: 100%;
        height: 100%;
        display: grid;
        place-items: center;
        align-content: center;
        gap: 28px;
        overflow: hidden;
        color: #291b12;
        background:
          radial-gradient(circle at 50% 38%, rgba(224, 164, 72, 0.24), transparent 28%),
          radial-gradient(circle at 50% 115%, rgba(177, 63, 46, 0.18), transparent 38%),
          #fbf5e8;
      }

      .splash.mark-only {
        background: transparent;
        gap: 0;
      }

      .splash.dark {
        color: #fff4e0;
        background:
          radial-gradient(circle at 50% 36%, rgba(230, 168, 60, 0.22), transparent 30%),
          radial-gradient(circle at 50% 115%, rgba(177, 63, 46, 0.22), transparent 40%),
          #100b06;
      }

      .splash.mark-only.dark {
        background: transparent;
      }

      /* The app icon's galaxy, drawn face-on and tilted here so it can turn
         without the tilt turning with it. Light theme draws it as soft ink
         on cream over a sunlit halo; dark theme as light, like the icon. */
      .galaxy-mark {
        position: relative;
        width: min(58vw, 240px);
        aspect-ratio: 1;
        display: grid;
        place-items: center;
      }

      .halo {
        position: absolute;
        inset: -10%;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(255, 226, 160, 0.7) 0%, rgba(240, 184, 90, 0.22) 24%, rgba(224, 164, 72, 0.08) 46%, transparent 64%);
        pointer-events: none;
      }

      .dark .halo {
        inset: -6%;
        background: radial-gradient(circle, rgba(255, 211, 106, 0.16), transparent 62%);
      }

      .mark-only .galaxy-mark {
        width: 100%;
        height: 100%;
      }

      .tilt {
        position: relative;
        width: 100%;
        height: 100%;
        transform: rotate(-24deg) scaleY(0.78);
      }

      .galaxy {
        width: 100%;
        height: 100%;
        display: block;
        filter: contrast(1.35) saturate(1.05) brightness(0.95);
        animation: galaxySpin 36s linear infinite;
      }

      .dark .galaxy {
        filter: none;
      }

      .glow {
        position: absolute;
        inset: 0;
        margin: auto;
        width: 22%;
        height: 22%;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(255, 246, 210, 0.95), rgba(240, 184, 74, 0.45) 45%, transparent 72%);
        animation: coreBreathe 2.6s ease-in-out infinite;
        pointer-events: none;
      }

      .dark .glow {
        background: radial-gradient(circle, rgba(255, 240, 200, 0.55), rgba(255, 200, 110, 0.18) 45%, transparent 70%);
      }

      .copy {
        display: grid;
        gap: 8px;
        text-align: center;
        animation: copyRise 720ms ease-out 180ms both;
      }

      h1 {
        margin: 0;
        justify-self: center;
        /* --text-zoom undoes the phone's font-size setting (matchDesignedTextSize). */
        font-size: calc(clamp(42px, 13vw, 72px) / var(--text-zoom, 1));
        font-weight: 500;
        letter-spacing: 0;
        line-height: 0.94;
      }

      .splash:not(.dark) h1 {
        color: #a8583c;
        /* The wordmark is a mask, so the gradient shows through its letters. */
        background: linear-gradient(180deg, #c98a52 0%, #b0623f 55%, #96482f 100%);
      }

      .splash:not(.dark) p {
        color: #8a6a55;
      }

      p {
        margin: 0;
        color: color-mix(in srgb, currentColor 70%, transparent);
        font: 700 calc(13px / var(--text-zoom, 1)) / 1.4 'Inter', system-ui, sans-serif;
        letter-spacing: 0.16em;
        text-transform: uppercase;
      }

      @keyframes galaxySpin {
        to {
          transform: rotate(-360deg);
        }
      }

      @keyframes coreBreathe {
        0%,
        100% {
          transform: scale(0.92);
          opacity: 0.85;
        }
        50% {
          transform: scale(1.1);
          opacity: 1;
        }
      }

      @keyframes copyRise {
        from {
          transform: translateY(18px);
          opacity: 0;
        }
        to {
          transform: translateY(0);
          opacity: 1;
        }
      }

      @media (prefers-reduced-motion: reduce) {
        .galaxy,
        .glow,
        .copy {
          animation: none;
        }
      }
    `,
  ],
})
export class SplashComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input() dark = false;
  @Input() appName = 'Siddha';
  @Input() tagline = 'Your Guide to Living in Rhythm';
  @Input() duration = 5000;
  @Input() markOnly = false;
  @Output() readonly finished = new EventEmitter<void>();
  @ViewChild('galaxy') private galaxy?: ElementRef<HTMLCanvasElement>;

  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private timer: ReturnType<typeof setTimeout> | null = null;

  ngOnChanges(): void {
    this.paintGalaxy();
  }

  ngAfterViewInit(): void {
    this.matchDesignedTextSize();
    this.paintGalaxy();
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    this.timer = setTimeout(() => this.finished.emit(), reduceMotion ? 900 : this.duration);
  }

  /**
   * Android's font-size setting scales WebView text (MainActivity.applyTextZoom),
   * so at 90% the wordmark came out smaller than the design while the mark did
   * not. The splash is artwork, not reading text: measure the zoom and divide
   * it back out.
   */
  private matchDesignedTextSize(): void {
    const host = this.host.nativeElement;
    const probe = document.createElement('span');
    probe.style.cssText = 'position:absolute;visibility:hidden;font-size:100px;line-height:1;';
    probe.textContent = 'M';
    host.appendChild(probe);
    const zoom = probe.getBoundingClientRect().height / 100;
    probe.remove();
    if (zoom > 0.5 && zoom < 2 && Math.abs(zoom - 1) > 0.02) {
      host.style.setProperty('--text-zoom', zoom.toFixed(3));
    }
  }

  ngOnDestroy(): void {
    if (this.timer) clearTimeout(this.timer);
  }

  /** Draw at 1024 px, as the icon does, then scale into the canvas. */
  private paintGalaxy(): void {
    const canvas = this.galaxy?.nativeElement;
    const out = canvas?.getContext('2d');
    if (!canvas || !out) return;
    try {
      const big = document.createElement('canvas');
      big.width = big.height = 1024;
      drawGalaxy(big, {
        theme: this.dark ? 'night' : 'day',
        background: false,
        shine: this.dark ? 2 : 1.8,
        weight: this.dark ? 1 : 1.5,
        tilt: 0,
        squash: 1,
        zoom: 1.02,
      });
      out.clearRect(0, 0, canvas.width, canvas.height);
      out.imageSmoothingQuality = 'high';
      out.drawImage(big, 0, 0, canvas.width, canvas.height);
    } catch {
      // A failed drawing leaves the wordmark and tagline on their own.
    }
  }
}
