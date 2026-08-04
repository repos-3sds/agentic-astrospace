import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnDestroy,
  Output,
} from '@angular/core';

@Component({
  selector: 'app-splash',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="splash" [class.dark]="dark" [class.mark-only]="markOnly" aria-label="SIDDHA loading">
      <svg class="siddha-mark" viewBox="0 0 320 320" role="img" aria-label="Siddha solar system mark">
        <defs>
          <radialGradient id="splashSun" cx="50%" cy="42%" r="58%">
            <stop offset="0%" stop-color="#fff6c7" />
            <stop offset="48%" stop-color="#e6a83c" />
            <stop offset="100%" stop-color="#b64a2d" />
          </radialGradient>
          <linearGradient id="splashOrbit" x1="56" x2="264" y1="80" y2="240">
            <stop offset="0%" stop-color="#d7b06a" stop-opacity="0.22" />
            <stop offset="52%" stop-color="#f3dcc3" stop-opacity="0.68" />
            <stop offset="100%" stop-color="#b94733" stop-opacity="0.22" />
          </linearGradient>
          <filter id="splashGlow" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="9" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <circle class="outer-halo" cx="160" cy="160" r="118" />
        <g class="orbit orbit-one">
          <ellipse cx="160" cy="160" rx="102" ry="42" />
          <circle class="planet planet-one" cx="262" cy="160" r="8" />
        </g>
        <g class="orbit orbit-two">
          <ellipse cx="160" cy="160" rx="88" ry="32" />
          <circle class="planet planet-two" cx="72" cy="160" r="5" />
        </g>
        <g class="orbit orbit-three">
          <ellipse cx="160" cy="160" rx="72" ry="116" />
          <circle class="planet planet-three" cx="160" cy="44" r="6" />
        </g>
        <circle class="sun" cx="160" cy="160" r="36" />
        <circle class="sun-core" cx="160" cy="160" r="17" />
        <path class="ray ray-a" d="M160 78v34M160 208v34M78 160h34M208 160h34" />
        <path class="ray ray-b" d="M102 102l24 24M194 194l24 24M218 102l-24 24M126 194l-24 24" />
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

      .siddha-mark {
        width: min(58vw, 240px);
        aspect-ratio: 1;
        overflow: visible;
      }

      .mark-only .siddha-mark {
        width: 100%;
        height: 100%;
      }

      .outer-halo {
        fill: none;
        stroke: rgba(178, 114, 52, 0.16);
        stroke-width: 1.5;
      }

      .orbit {
        transform-box: fill-box;
        transform-origin: center;
        animation: orbitSpin 8s linear infinite;
      }

      .orbit-two {
        animation-duration: 11s;
        animation-direction: reverse;
      }

      .orbit-three {
        animation-duration: 13s;
      }

      .orbit ellipse {
        fill: none;
        stroke: url(#splashOrbit);
        stroke-width: 2;
      }

      .planet {
        fill: #f5d69a;
        filter: url(#splashGlow);
      }

      .planet-two {
        fill: #bc6a48;
      }

      .planet-three {
        fill: #fff1c7;
      }

      .sun {
        fill: url(#splashSun);
        filter: url(#splashGlow);
        transform-box: fill-box;
        transform-origin: center;
        animation: sunBreathe 2.4s ease-in-out infinite;
      }

      .sun-core {
        fill: rgba(255, 247, 208, 0.86);
      }

      .ray {
        fill: none;
        stroke: currentColor;
        stroke-linecap: round;
        stroke-width: 3;
        opacity: 0.36;
        transform-box: fill-box;
        transform-origin: center;
      }

      .ray-b {
        opacity: 0.24;
      }

      .copy {
        display: grid;
        gap: 8px;
        text-align: center;
        animation: copyRise 720ms ease-out 180ms both;
      }

      h1 {
        margin: 0;
        font-family: 'Samarkan', 'Cormorant Garamond', serif;
        font-size: clamp(42px, 13vw, 72px);
        font-weight: 500;
        letter-spacing: 0;
        line-height: 0.94;
      }

      p {
        margin: 0;
        color: color-mix(in srgb, currentColor 70%, transparent);
        font: 700 13px/1.4 'Inter', system-ui, sans-serif;
        letter-spacing: 0.16em;
        text-transform: uppercase;
      }

      @keyframes sunBreathe {
        0%,
        100% {
          transform: scale(0.96);
          opacity: 0.94;
        }
        50% {
          transform: scale(1.08);
          opacity: 1;
        }
      }

      @keyframes orbitSpin {
        to {
          transform: rotate(360deg);
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
        .orbit,
        .sun,
        .copy {
          animation: none;
        }
      }
    `,
  ],
})
export class SplashComponent implements AfterViewInit, OnDestroy {
  @Input() dark = false;
  @Input() appName = 'SIDDHA';
  @Input() tagline = 'Your Guide to Living in Rhythm';
  @Input() duration = 5000;
  @Input() markOnly = false;
  @Output() readonly finished = new EventEmitter<void>();

  private timer: ReturnType<typeof setTimeout> | null = null;

  ngAfterViewInit(): void {
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    this.timer = setTimeout(() => this.finished.emit(), reduceMotion ? 900 : this.duration);
  }

  ngOnDestroy(): void {
    if (this.timer) clearTimeout(this.timer);
  }
}
