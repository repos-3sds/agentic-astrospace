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
            <circle class="star twinkle" [attr.cx]="s.x + '%'" [attr.cy]="s.y + '%'" [attr.r]="s.r"
              [attr.opacity]="s.opacity" [style.animation-delay.s]="s.delay" />
          }
        </svg>
      }
      <svg class="siddha-mark" viewBox="0 0 100 100" role="img" aria-label="Siddha">
        <defs>
          <radialGradient [attr.id]="id + '-haze'" cx="50%" cy="50%" r="50%">
            <stop class="haze-a" offset="0" />
            <stop class="haze-b" offset=".55" />
            <stop offset="1" stop-color="#000" stop-opacity="0" />
          </radialGradient>
          <radialGradient [attr.id]="id + '-core'">
            <stop class="core-a" offset="0" />
            <stop class="core-b" offset=".3" />
            <stop class="core-c" offset="1" />
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
          @for (s of field; track $index) {
            <circle class="star twinkle" [attr.cx]="s.x" [attr.cy]="s.y" [attr.r]="s.r"
              [attr.opacity]="s.opacity" [style.animation-delay.s]="s.delay" />
          }
        }
        <g class="galaxy">
          <ellipse cx="50" cy="50" rx="44" ry="36" [attr.fill]="'url(#' + id + '-haze)'" />
          <g class="spin">
            <g [attr.filter]="'url(#' + id + '-glow)'" transform="rotate(-24 50 50)">
              @for (d of arms; track $index) {
                <circle [class]="d.graha ? 'graha' : 'dot'" [attr.cx]="d.x" [attr.cy]="d.y" [attr.r]="d.r"
                  [attr.opacity]="d.opacity"
                  [style.animation-delay.s]="d.delay" />
              }
            </g>
          </g>
          <g class="core">
            <circle cx="50" cy="50" r="11" [attr.fill]="'url(#' + id + '-core)'" />
            <circle class="core-dot" cx="50" cy="50" r="2.6" />
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

      /* Adaptive: space black in dark mode, porcelain sky in light mode, the
         same galaxy redrawn in each so it never sits on the page as a patch. */
      :host {
        --g-text: #141a33;
        --g-muted: rgba(20, 26, 51, 0.62);
        --g-ground:
          radial-gradient(circle at 50% 40%, rgba(233, 185, 73, 0.16), transparent 34%),
          radial-gradient(circle at 50% 46%, #ffffff, #f4f5fa 60%, #e6e9f5 100%);
        --g-dot: #c18d1a;
        --g-graha: #8a5d00;
        --g-star: #2b3770;
        --g-star-alpha: 0.5;
        --g-haze-a: rgba(233, 185, 73, 0.26);
        --g-haze-b: rgba(91, 63, 160, 0.06);
        --g-core-a: #fff8e2;
        --g-core-b: #f2c24f;
        --g-core-c: rgba(233, 185, 73, 0);
        --g-core-dot: #fffaf0;
      }

      :host-context(.app-dark) {
        --g-text: #f4ead2;
        --g-muted: rgba(244, 234, 210, 0.66);
        --g-ground:
          radial-gradient(circle at 50% 40%, rgba(233, 185, 73, 0.1), transparent 34%),
          radial-gradient(circle at 50% 46%, #0d0b18, #05050b 60%, #000 100%);
        --g-dot: #e9b949;
        --g-graha: #fff4d6;
        --g-star: #ffffff;
        --g-star-alpha: 1;
        --g-haze-a: rgba(233, 185, 73, 0.18);
        --g-haze-b: rgba(91, 63, 160, 0.07);
        --g-core-a: #ffffff;
        --g-core-b: #ffe7a6;
        --g-core-c: rgba(233, 185, 73, 0);
        --g-core-dot: #ffffff;
      }

      .splash {
        width: 100%;
        height: 100%;
        display: grid;
        place-items: center;
        align-content: center;
        gap: 28px;
        overflow: hidden;
        color: var(--g-text);
        background: var(--g-ground);
      }

      .dot { fill: var(--g-dot); }
      .graha { fill: var(--g-graha); }
      .star { fill: var(--g-star); }
      .star { fill-opacity: var(--g-star-alpha); }
      .haze-a { stop-color: var(--g-haze-a); }
      .haze-b { stop-color: var(--g-haze-b); }
      .core-a { stop-color: var(--g-core-a); }
      .core-b { stop-color: var(--g-core-b); }
      .core-c { stop-color: var(--g-core-c); }
      .core-dot { fill: var(--g-core-dot); }

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

      .mark-only .siddha-mark {
        width: 100%;
        height: 100%;
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
        color: var(--g-muted);
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
