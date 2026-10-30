import { ChangeDetectionStrategy, Component, ElementRef, inject, signal, viewChild } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ThemeService } from '../../../core/theme.service';

interface IntroSlide {
  key: string;
  eyebrow: string;
  title: string;
  detail: string;
  /** A second screen laid over the first, for the slide that shows two features. */
  second?: string;
}

/**
 * The app's front door: four swipes that show what Siddha does before it
 * asks for anything (onboarding plan 2026-10-30, replacing the old Landing
 * hero and the Welcome screen that repeated it).
 *
 * Each slide is a real screen from the app, captured in light and dark
 * (public/intro), not an illustration, so nothing promised here is missing
 * later. Skip is always there; the last slide carries both ways in. New
 * readers go to the promise and choices screen before the account.
 */
@Component({
  selector: 'as-landing',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    @if (deleted) {
      <p class="deleted" role="status">Your account and everything in it have been deleted.</p>
    }
    <header class="topbar">
      @if (index() < slides.length - 1) {
        <button class="skip" type="button" (click)="go(slides.length - 1)">Skip</button>
      }
    </header>

    <div class="track" #track (scroll)="onScroll()" aria-roledescription="carousel" aria-label="What Siddha does">
      @for (slide of slides; track slide.key; let i = $index) {
        <section class="slide" [attr.aria-label]="(i + 1) + ' of ' + slides.length" [attr.aria-hidden]="i !== index()">
          <div class="peek" [class.has-second]="!!slide.second">
            <img class="screen" [src]="image(slide.key)" alt="" />
            @if (slide.second) {
              <img class="screen second" [src]="image(slide.second)" alt="" />
            }
          </div>
          <div class="copy">
            <p class="eyebrow">{{ slide.eyebrow }}</p>
            <h1 class="headline">{{ slide.title }}</h1>
            <p class="lede">{{ slide.detail }}</p>
          </div>
        </section>
      }
    </div>

    <footer class="actions">
      <div class="dots" aria-hidden="true">
        @for (slide of slides; track slide.key; let i = $index) {
          <i [class.on]="i === index()"></i>
        }
      </div>
      @if (index() < slides.length - 1) {
        <button class="btn primary" type="button" (click)="go(index() + 1)">Next</button>
      } @else {
        <a class="btn primary" [routerLink]="['/m', 'disclaimers']" [queryParams]="{ then: 'register' }">Begin your path</a>
        <a class="btn tertiary" [routerLink]="['/m', 'auth']" [queryParams]="{ mode: 'signin' }">I already have an account</a>
      }
    </footer>
  `,
  styleUrl: './landing.component.scss',
  // Outside the shell, so the token host class must be applied here or every
  // var() silently falls back — see the build plan's first convention.
  host: { class: 'as-mobile' },
})
export class LandingComponent {
  protected readonly theme = inject(ThemeService);
  /** Set by account deletion, read once: nothing said the deletion went through (U32). */
  protected readonly deleted = takeDeletedFlag();
  protected readonly index = signal(0);
  private readonly track = viewChild.required<ElementRef<HTMLElement>>('track');

  protected readonly slides: IntroSlide[] = [
    {
      key: 'today',
      eyebrow: 'Today',
      title: 'Your day, read from your chart',
      detail: 'A calm reading each morning: how the day feels, what to do, and what to avoid.',
    },
    {
      key: 'calendar',
      second: 'muhurta',
      eyebrow: 'Good times',
      title: 'Know the good hours and days',
      detail: 'Rahu Kalam, festivals and the best day to buy, sign or begin, for your own city.',
    },
    {
      key: 'ask',
      eyebrow: 'Ask',
      title: 'Ask about your life',
      detail: 'Work, marriage, money, family. A plain answer from your own chart, never fear.',
    },
    {
      key: 'remedies',
      eyebrow: 'Practice',
      title: 'Small practices that help',
      detail: 'Mantras and simple steps for this part of your life. Nothing to buy, nothing to remove.',
    },
  ];

  protected image(key: string): string {
    return `intro/${key}-${this.theme.dark() ? 'dark' : 'light'}.webp`;
  }

  protected go(i: number): void {
    const track = this.track().nativeElement;
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    track.scrollTo({ left: i * track.clientWidth, behavior: reduce ? 'auto' : 'smooth' });
    this.index.set(i);
  }

  protected onScroll(): void {
    const track = this.track().nativeElement;
    if (!track.clientWidth) return;
    this.index.set(Math.round(track.scrollLeft / track.clientWidth));
  }
}

// Not under 'astrospace.': sign-out clears those from sessionStorage.
export const ACCOUNT_DELETED_FLAG = 'siddha.accountDeleted';

function takeDeletedFlag(): boolean {
  try {
    const set = sessionStorage.getItem(ACCOUNT_DELETED_FLAG) === '1';
    sessionStorage.removeItem(ACCOUNT_DELETED_FLAG);
    return set;
  } catch {
    return false;
  }
}
