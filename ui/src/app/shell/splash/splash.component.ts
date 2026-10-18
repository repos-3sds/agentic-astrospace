import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnDestroy,
  Output,
} from '@angular/core';

let nextSplashId = 0;

/**
 * The launch splash and the landing mark: the app icon's light-ribbon galaxy
 * (ic_launcher, 2026-10-16), turning slowly, with the Siddha wordmark under it.
 * Light and dark are one design in two moods (Hawk, 2026-10-18): soft pastel
 * ribbons on an ivory sunrise in light, gold and cream on near-black in dark.
 * The wordmark is terracotta or gold, never black.
 */
@Component({
  selector: 'app-splash',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="splash" [class.dark]="dark" [class.mark-only]="markOnly" aria-label="Siddha loading">
      <svg class="siddha-mark" viewBox="0 0 320 320" role="img" aria-label="Siddha galaxy mark">
        <defs>
          <linearGradient [attr.id]="id + 'ribbon'" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" class="r1" stop-opacity="0" />
            <stop offset="0.35" class="r1" stop-opacity="0.9" />
            <stop offset="0.6" class="r2" stop-opacity="1" />
            <stop offset="1" class="r3" stop-opacity="0.15" />
          </linearGradient>
          <radialGradient [attr.id]="id + 'core'" cx="50%" cy="50%" r="50%">
            <stop offset="0" stop-color="#fffbea" />
            <stop offset="0.35" stop-color="#ffe2a0" />
            <stop offset="0.7" stop-color="#f0a646" stop-opacity="0.55" />
            <stop offset="1" stop-color="#f0a646" stop-opacity="0" />
          </radialGradient>
          <filter [attr.id]="id + 'glow'" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2.4" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter [attr.id]="id + 'soft'" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="7" />
          </filter>
        </defs>

        <circle class="halo" cx="160" cy="160" r="70" [attr.fill]="url('core')" [attr.filter]="url('soft')" />
        <g class="spin ribbons" [attr.filter]="url('glow')" [attr.stroke]="url('ribbon')">
          <ellipse cx="160" cy="160" rx="132" ry="74" stroke-width="2.2" transform="rotate(-24 160 160)" />
          <ellipse cx="160" cy="160" rx="116" ry="62" stroke-width="2.6" transform="rotate(-8 160 160)" />
          <ellipse cx="160" cy="160" rx="98" ry="52" stroke-width="3" transform="rotate(10 160 160)" />
          <ellipse cx="160" cy="160" rx="80" ry="42" stroke-width="3.2" transform="rotate(26 160 160)" />
          <ellipse cx="160" cy="160" rx="62" ry="32" stroke-width="3.4" transform="rotate(42 160 160)" />
          <circle class="star twinkle" cx="282" cy="108" r="3.6" />
          <circle class="star twinkle b" cx="58" cy="214" r="3" />
          <circle class="star twinkle c" cx="236" cy="226" r="2.6" />
          <circle class="star" cx="96" cy="96" r="2.2" />
        </g>
        <g class="spin highlight">
          <ellipse cx="160" cy="160" rx="116" ry="62" stroke-width="1" transform="rotate(-8 160 160)" />
          <ellipse cx="160" cy="160" rx="80" ry="42" stroke-width="1.2" transform="rotate(26 160 160)" />
        </g>
        <g class="core-arms" [attr.filter]="url('glow')">
          <path d="M160 160 C 196 128, 214 168, 188 186 C 168 200, 138 194, 128 176" />
          <path d="M160 160 C 124 192, 106 152, 132 134 C 152 120, 182 126, 192 144" />
        </g>
        <circle class="core-dot" cx="160" cy="160" r="12" [attr.filter]="url('glow')" />
      </svg>

      @if (!markOnly) {
        <div class="copy">
          <h1>{{ appName }}</h1>
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
        /* Light: an ivory sunrise and soft pastel ribbons. */
        --r1: #e3b46e;
        --r2: #c97a63;
        --r3: #b39ac8;
        --arm: #efbd6b;
        --star: #d9a273;
        --wordmark: #b25a45;
        --tagline: #8a6f5c;
        width: 100%;
        height: 100%;
        display: grid;
        place-items: center;
        align-content: center;
        gap: 30px;
        overflow: hidden;
        color: #3a2a1f;
        background:
          radial-gradient(circle at 50% 41%, rgba(255, 224, 170, 0.42), rgba(255, 224, 170, 0) 30%),
          radial-gradient(120% 70% at 50% 110%, rgba(226, 150, 118, 0.14), transparent 60%),
          linear-gradient(180deg, #fffcf6 0%, #fcf5ea 60%, #f8ece0 100%);
      }

      .splash.dark {
        /* Dark: the icon itself, gold and cream light on near-black. */
        --r1: #f3c978;
        --r2: #fff1cf;
        --r3: #a77ad6;
        --arm: #ffd98a;
        --star: #fff0c9;
        --wordmark: #f4d9a6;
        --tagline: rgba(255, 244, 224, 0.72);
        color: #fff4e0;
        background:
          radial-gradient(circle at 50% 40%, rgba(230, 168, 60, 0.16), transparent 34%),
          radial-gradient(circle at 50% 115%, rgba(120, 60, 140, 0.18), transparent 42%),
          #0b0806;
      }

      .splash.mark-only,
      .splash.mark-only.dark {
        background: transparent;
        gap: 0;
      }

      .siddha-mark {
        width: min(64vw, 260px);
        aspect-ratio: 1;
        overflow: visible;
      }

      .splash:not(.dark) .siddha-mark {
        filter: drop-shadow(0 6px 22px rgba(214, 150, 90, 0.18));
      }

      .mark-only .siddha-mark {
        width: 100%;
        height: 100%;
      }

      .r1 { stop-color: var(--r1); }
      .r2 { stop-color: var(--r2); }
      .r3 { stop-color: var(--r3); }

      .halo { opacity: 0.9; }

      .ribbons {
        fill: none;
        stroke-linecap: round;
      }

      .star {
        fill: var(--star);
        stroke: none;
      }

      /* A fine bright line inside two ribbons, so in light they read as light. */
      .highlight {
        fill: none;
        stroke: #fffaf0;
        opacity: 0.9;
      }

      .dark .highlight { display: none; }

      .core-arms {
        fill: none;
        stroke: var(--arm);
        stroke-width: 5;
        stroke-linecap: round;
        transform-origin: 160px 160px;
        animation: spin 24s linear infinite reverse;
      }

      .core-dot { fill: #fffbea; }

      /* The icon's motion: the galaxy turns slowly, the core counter-turns. */
      .spin {
        transform-origin: 160px 160px;
        animation: spin 48s linear infinite;
      }

      .twinkle { animation: twinkle 3.6s ease-in-out infinite; }
      .twinkle.b { animation-delay: 1.2s; }
      .twinkle.c { animation-delay: 2.4s; }

      .copy {
        display: grid;
        gap: 12px;
        text-align: center;
        animation: copyRise 720ms ease-out 180ms both;
      }

      h1 {
        margin: 0;
        color: var(--wordmark);
        font-family: 'Samarkan', 'Cormorant Garamond', serif;
        font-size: clamp(46px, 14vw, 72px);
        font-weight: 400;
        letter-spacing: 0;
        line-height: 1;
      }

      p {
        margin: 0;
        color: var(--tagline);
        font: 600 12.5px/1.4 'Inter', system-ui, sans-serif;
        letter-spacing: 0.2em;
        text-transform: uppercase;
      }

      @keyframes spin {
        to { transform: rotate(360deg); }
      }

      @keyframes twinkle {
        50% { opacity: 0.35; }
      }

      @keyframes copyRise {
        from { transform: translateY(18px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
      }

      @media (prefers-reduced-motion: reduce) {
        .spin,
        .core-arms,
        .twinkle,
        .copy {
          animation: none;
        }
      }
    `,
  ],
})
export class SplashComponent implements AfterViewInit, OnDestroy {
  /** SVG ids are document-wide; the mark is on screen twice (splash and landing). */
  protected readonly id = `siddha-splash-${nextSplashId++}-`;
  @Input() dark = false;
  @Input() appName = 'Siddha';
  @Input() tagline = 'Your Guide to Living in Rhythm';
  @Input() duration = 5000;
  @Input() markOnly = false;
  @Output() readonly finished = new EventEmitter<void>();

  private timer: ReturnType<typeof setTimeout> | null = null;

  ngAfterViewInit(): void {
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    this.timer = setTimeout(() => this.finished.emit(), reduceMotion ? 900 : this.duration);
  }

  protected url(name: string): string {
    return `url(#${this.id}${name})`;
  }

  ngOnDestroy(): void {
    if (this.timer) clearTimeout(this.timer);
  }
}
