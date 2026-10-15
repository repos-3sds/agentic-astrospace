import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnDestroy,
  Output,
} from '@angular/core';

interface Dot {
  x: number;
  y: number;
  r: number;
  opacity: number;
  graha: boolean;
  delay: number;
}

const TAU = Math.PI * 2;

// The Siddha mark: the Nine-Arm Galaxy. Two dotted spiral arms carry eight
// bright graha stars and the glowing core is the ninth. The same geometry is
// rendered into the app icons and native splash images, so keep it in step
// with ui/scripts/brand/galaxy.cjs (see docs/native_builds.md).
function galaxyArms(): Dot[] {
  const dots: Dot[] = [];
  for (let arm = 0; arm < 2; arm++) {
    for (let k = 0; k < 46; k++) {
      const t = k / 45;
      const a = arm * Math.PI + t * 1.42 * TAU;
      const r = 4 + t * 38;
      const graha = k % 10 === 6;
      dots.push({
        x: 50 + r * Math.cos(a),
        y: 50 + r * Math.sin(a) * 0.78,
        r: graha ? 2.1 : 1.15 - t * 0.7,
        opacity: graha ? 1 : 1 - t * 0.65,
        graha,
        delay: graha ? ((k + arm * 23) % 9) * 0.37 : 0,
      });
    }
  }
  return dots;
}

function starField(count = 26, seed = 13, scale = 1): Dot[] {
  const next = () => {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  };
  return Array.from({ length: count }, (_, i) => ({
    x: next() * 100,
    y: next() * 100,
    r: (0.3 + (i % 3) * 0.18) * scale,
    opacity: 0.25 + (i % 4) * 0.15,
    graha: false,
    delay: (i * 0.29) % 3,
  }));
}

const ARMS = galaxyArms();
const FIELD = starField();
// The intro's sky spans the whole screen; radii here are in CSS pixels.
const SKY = starField(140, 29, 2.2);
let instances = 0;

@Component({
  selector: 'app-splash',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="splash" [class.mark-only]="markOnly" aria-label="Siddha loading">
      @if (!markOnly) {
        <svg class="sky" aria-hidden="true">
          @for (s of sky; track $index) {
            <circle class="twinkle" [attr.cx]="s.x + '%'" [attr.cy]="s.y + '%'" [attr.r]="s.r" fill="#fff"
              [attr.opacity]="s.opacity" [style.animation-delay.s]="s.delay" />
          }
        </svg>
      }
      <svg class="siddha-mark" viewBox="0 0 100 100" role="img" aria-label="Siddha">
        <defs>
          <radialGradient [attr.id]="id + '-bg'" cx="50%" cy="46%" r="75%">
            <stop offset="0" stop-color="#0d0b18" />
            <stop offset=".6" stop-color="#05050b" />
            <stop offset="1" stop-color="#000000" />
          </radialGradient>
          <radialGradient [attr.id]="id + '-haze'" cx="50%" cy="50%" r="50%">
            <stop offset="0" stop-color="#e9b949" stop-opacity=".18" />
            <stop offset=".55" stop-color="#5b3fa0" stop-opacity=".07" />
            <stop offset="1" stop-color="#000" stop-opacity="0" />
          </radialGradient>
          <radialGradient [attr.id]="id + '-core'">
            <stop offset="0" stop-color="#ffffff" />
            <stop offset=".3" stop-color="#ffe7a6" />
            <stop offset="1" stop-color="#e9b949" stop-opacity="0" />
          </radialGradient>
          <filter [attr.id]="id + '-glow'" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="1.2" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        @if (markOnly) {
          <rect width="100" height="100" rx="22.5" [attr.fill]="'url(#' + id + '-bg)'" />
          @for (s of field; track $index) {
            <circle class="twinkle" [attr.cx]="s.x" [attr.cy]="s.y" [attr.r]="s.r" fill="#fff"
              [attr.opacity]="s.opacity" [style.animation-delay.s]="s.delay" />
          }
        }
        <g class="galaxy">
          <ellipse cx="50" cy="50" rx="44" ry="36" [attr.fill]="'url(#' + id + '-haze)'" />
          <g class="spin">
            <g [attr.filter]="'url(#' + id + '-glow)'" transform="rotate(-24 50 50)">
              @for (d of arms; track $index) {
                <circle [class.graha]="d.graha" [attr.cx]="d.x" [attr.cy]="d.y" [attr.r]="d.r"
                  [attr.fill]="d.graha ? '#fff4d6' : '#e9b949'" [attr.opacity]="d.opacity"
                  [style.animation-delay.s]="d.delay" />
              }
            </g>
          </g>
          <g class="core">
            <circle cx="50" cy="50" r="11" [attr.fill]="'url(#' + id + '-core)'" />
            <circle cx="50" cy="50" r="2.6" fill="#fff" />
          </g>
        </g>
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

      /* Space black in both themes: the intro is the galaxy, not the app chrome. */
      .splash {
        width: 100%;
        height: 100%;
        display: grid;
        place-items: center;
        align-content: center;
        gap: 28px;
        overflow: hidden;
        color: #f4ead2;
        background:
          radial-gradient(circle at 50% 40%, rgba(233, 185, 73, 0.1), transparent 34%),
          radial-gradient(circle at 50% 46%, #0d0b18, #05050b 60%, #000 100%);
      }

      .splash {
        position: relative;
      }

      .sky {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
      }

      .siddha-mark,
      .copy {
        position: relative;
      }

      .splash.mark-only {
        background: transparent;
        gap: 0;
        overflow: visible;
      }

      .siddha-mark {
        width: min(72vw, 300px);
        aspect-ratio: 1;
        overflow: visible;
        animation: markRise 1.4s cubic-bezier(0.2, 0.8, 0.2, 1) both;
      }

      /* The old sun mark drew inside ~75% of its box; the tile keeps that footprint. */
      .mark-only .siddha-mark {
        width: 78%;
        height: 78%;
        overflow: hidden;
        border-radius: 22.5%;
        animation: none;
      }

      .spin,
      .core {
        transform-origin: 50px 50px;
      }

      .spin {
        animation: spin 48s linear infinite;
      }

      .core {
        animation: breathe 4.8s ease-in-out infinite;
      }

      .graha {
        transform-box: fill-box;
        transform-origin: center;
        animation: pulse 3.3s ease-in-out infinite;
      }

      .twinkle {
        animation: twinkle 3s ease-in-out infinite;
      }

      .copy {
        display: grid;
        gap: 8px;
        text-align: center;
        animation: copyRise 900ms ease-out 600ms both;
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
        color: rgba(244, 234, 210, 0.66);
        font: 700 13px/1.4 'Inter', system-ui, sans-serif;
        letter-spacing: 0.16em;
        text-transform: uppercase;
      }

      @keyframes markRise {
        from {
          transform: scale(0.72) rotate(-40deg);
          opacity: 0;
        }
        to {
          transform: scale(1) rotate(0deg);
          opacity: 1;
        }
      }

      @keyframes spin {
        to {
          transform: rotate(360deg);
        }
      }

      @keyframes pulse {
        0%,
        100% {
          transform: scale(1);
          opacity: 1;
        }
        50% {
          transform: scale(1.3);
          opacity: 0.75;
        }
      }

      @keyframes twinkle {
        0%,
        100% {
          opacity: 0.15;
        }
        50% {
          opacity: 0.85;
        }
      }

      @keyframes breathe {
        0%,
        100% {
          transform: scale(1);
          opacity: 0.9;
        }
        50% {
          transform: scale(1.18);
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
        .siddha-mark,
        .spin,
        .core,
        .graha,
        .twinkle,
        .copy {
          animation: none;
        }
      }
    `,
  ],
})
export class SplashComponent implements AfterViewInit, OnDestroy {
  @Input() appName = 'Siddha';
  @Input() tagline = 'Your Guide to Living in Rhythm';
  @Input() duration = 5000;
  @Input() markOnly = false;
  @Output() readonly finished = new EventEmitter<void>();

  protected readonly arms = ARMS;
  protected readonly field = FIELD;
  protected readonly sky = SKY;
  // Gradient and filter ids are document-global; the intro and the onboarding
  // mark can be on screen together, so each instance gets its own.
  protected readonly id = `siddha-galaxy-${++instances}`;

  private timer: ReturnType<typeof setTimeout> | null = null;

  ngAfterViewInit(): void {
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    this.timer = setTimeout(() => this.finished.emit(), reduceMotion ? 900 : this.duration);
  }

  ngOnDestroy(): void {
    if (this.timer) clearTimeout(this.timer);
  }
}
