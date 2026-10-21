import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, computed, effect, inject, signal, untracked, viewChild } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import { App as CapacitorApp } from '@capacitor/app';
import {
  NavigationEnd,
  Router,
  RouterLink,
  RouterOutlet,
} from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { PlanGateService } from '../../../core/plan-gate.service';
import { filter, map, startWith } from 'rxjs';
import { KundliStore } from '../../../core/kundli.store';
import { GenericErrorComponent } from '../states/generic-error.component';
import { PreferencesService } from '../../../core/preferences.service';
import { SheetOverlayService } from '../../../core/sheet-overlay.service';
import { HapticsService } from '../../../core/haptics.service';
import { ConnectivityService } from '../../../core/connectivity.service';
import { ScrollMemoryDirective } from './scroll-memory.directive';
import { PullRefreshDirective } from './pull-refresh.directive';
import { Subhashita, SubhashitaService } from '../../../core/subhashita.service';
import { SubhashitaSheetComponent } from '../subhashita/subhashita-sheet.component';
import { WidgetBridgeService } from '../../../core/widget-bridge.service';
import { deepLinkArrivedAt } from '../../../core/deep-link-arrival';
import { activeTabRoots } from '../../../core/tab-roots';
import { AppLinksService } from '../../../core/app-links.service';

interface MobileTab {
  commands: string[];
  label: string;
  icon: string;
}

/** Screens reached from the Explore tab's menu. */
const EXPLORE_ROOTS = [
  '/m/chart', '/m/explore', '/m/transits', '/m/readings', '/m/notes',
  '/m/notifications', '/m/search', '/m/remedies', '/m/muhurta',
  '/m/compat', '/m/subhashita',
];

/** Screens reached from the Settings tab: its rows, Family and Plans. */
const SETTINGS_ROOTS = ['/m/settings', '/m/family', '/m/subscription'];

function under(path: string, root: string): boolean {
  return path === root || path.startsWith(`${root}/`);
}

/**
 * Native app shell: routed content plus the tab bar (Figma node 13:66) — five
 * tabs in every mode, Settings always last on the far right.
 *
 * The shell owns the safe areas. styles.scss has defined --as-safe-* since the
 * mobile UX pass but nothing consumed them, which is why the status bar and
 * home indicator showed as bare white bands in the simulator — the WebView's
 * own background, not the app's.
 */
const VERSE_SHEET_SETTLE_MS = 900;
const DEEP_LINK_WINDOW_MS = 15_000;

@Component({
  selector: 'as-mobile-shell',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, RouterLink, GenericErrorComponent, ScrollMemoryDirective, PullRefreshDirective, SubhashitaSheetComponent],
  templateUrl: './mobile-shell.component.html',
  styleUrl: './mobile-shell.component.scss',
  host: { class: 'as-mobile' },
})
export class MobileShellComponent {
  private readonly router = inject(Router);
  protected readonly kundlis = inject(KundliStore);
  protected readonly preferences = inject(PreferencesService);
  private readonly gate = inject(PlanGateService);
  // Practitioner mode is the Practitioner plan's. Once plans are enforced, a
  // reader without it (chosen in onboarding, or a plan that lapsed) is shown
  // Balanced; choosing it again in Settings opens Plans.
  private readonly practitionerPlan = effect(() => {
    if (this.preferences.experienceMode() === 'practitioner' && !this.gate.allows('practitioner.workflow')) {
      this.preferences.experienceMode.set('balanced');
    }
  });
  protected readonly overlay = inject(SheetOverlayService);
  private readonly haptics = inject(HapticsService);
  protected readonly connectivity = inject(ConnectivityService);
  private readonly scroller = viewChild(ScrollMemoryDirective);

  private readonly subhashita = inject(SubhashitaService);
  private readonly widgets = inject(WidgetBridgeService);
  /** Today's verse while its first-open sheet is up. */
  protected readonly dailyVerse = signal<Subhashita | null>(null);

  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  /** Read once per screen change by the live region when a screen has no h1. */
  protected readonly screenAnnouncement = signal('');
  private lastPath: string | null = null;

  constructor() {
    // Screen readers heard nothing when the screen changed and kept reading
    // from a detached element (audit N14). Like a native push, move focus to
    // the new screen's heading; query-only changes (a tab inside a screen)
    // stay where they are.
    effect(() => {
      const path = this.currentPath();
      untracked(() => {
        const previous = this.lastPath;
        this.lastPath = path;
        if (previous !== null && previous !== path) setTimeout(() => this.focusScreen(), 0);
      });
    });
    effect(() => activeTabRoots.set(this.tabs().map((tab) => `/m/${tab.commands.join('/')}`)));
    inject(DestroyRef).onDestroy(() => activeTabRoots.set([]));
    if (!this.kundlis.loaded()) void this.kundlis.load().catch(() => undefined);
    this.widgets.start();
    inject(AppLinksService).start();
    void this.offerDailyVerse();
    // A phone left with the app open overnight comes back without a cold
    // start, so the next morning's first look counts as the day's first open.
    if (Capacitor.isNativePlatform()) {
      const listener = CapacitorApp.addListener('appStateChange', ({ isActive }) => {
        if (isActive) void this.offerDailyVerse();
      });
      inject(DestroyRef).onDestroy(() => void listener.then((l) => l.remove()));
    }
  }

  private focusScreen(): void {
    if (this.overlay.open()) return;
    const heading = this.host.nativeElement.querySelector<HTMLElement>('main.content h1');
    if (heading) {
      if (!heading.hasAttribute('tabindex')) heading.setAttribute('tabindex', '-1');
      heading.focus({ preventScroll: true });
      this.screenAnnouncement.set('');
      return;
    }
    this.screenAnnouncement.set(document.title.replace(/ · Siddha$/, ''));
  }

  /**
   * Today's Subhashita, once a day on the first open (Hawk, 2026-10-17).
   * Not on a reader's very first day, which already opens on their first
   * reading; not over the verse's own screen or over another sheet.
   */
  private async offerDailyVerse(): Promise<void> {
    // Every open moves the verse on to today's date, so the Today card never
    // keeps yesterday's on a phone left open overnight. Cheap: the cache
    // answers unless it is short or holds another rotation.
    const loaded = this.subhashita.load();
    if (this.widgets.enabled) {
      // The verse widget holds two weeks ahead; each open tops it up.
      void loaded.then((verse) => {
        if (verse) this.widgets.publishSubhashita(this.subhashita.upcoming());
      }).catch(() => undefined);
    }
    if (!this.subhashita.sheetOn() || !this.subhashita.unseenToday()) return;
    if (this.subhashita.neverOffered()) {
      this.subhashita.markSeen();
      return;
    }
    const verse = await loaded;
    // A push or widget tap lands its route a moment after a cold start; give
    // it that moment, and don't cover where the reader asked to go (D8).
    await new Promise((resolve) => setTimeout(resolve, VERSE_SHEET_SETTLE_MS));
    if (!verse || !this.subhashita.unseenToday()) return;
    this.subhashita.markSeen();
    const fromTap = Date.now() - deepLinkArrivedAt() < DEEP_LINK_WINDOW_MS;
    if (fromTap || this.currentPath().startsWith('/m/subhashita') || this.overlay.open()) return;
    this.dailyVerse.set(verse);
  }

  protected turnOffVerseSheet(): void {
    this.subhashita.setSheetOn(false);
    this.dailyVerse.set(null);
  }

  /** The profile list failed and nothing is cached: every tab would be empty,
   * so the shell says so once instead of each screen guessing. */
  protected readonly profilesBlocked = computed(
    () => !!this.kundlis.loadError() && !this.kundlis.loaded() && this.kundlis.kundlis().length === 0,
  );

  protected retryProfiles(): void {
    void this.kundlis.load().catch(() => undefined);
  }

  /**
   * Tab roots keep the primary navigation; pushed detail screens do not. Route
   * data makes that layout decision explicit instead of teaching every detail
   * component how to cover or offset the shell.
   */
  protected readonly hideTabs = toSignal(
    this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd),
      startWith(null),
      map(() => {
        // RouterStateSnapshot is immutable for this navigation. Walking the
        // live ActivatedRoute tree here can race a redirect between reading
        // firstChild and assigning it, leaving the leaf undefined.
        let leaf = this.router.routerState.snapshot.root;
        while (leaf.firstChild) {
          leaf = leaf.firstChild;
        }
        return leaf.data['hideMobileTabs'] === true;
      }),
    ),
    { initialValue: false },
  );

  protected readonly currentPath = toSignal(
    this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd),
      startWith(null),
      map(() => this.router.url.split('?')[0]?.split('#')[0] || '/m/today'),
    ),
    { initialValue: this.router.url.split('?')[0]?.split('#')[0] || '/m/today' },
  );

  /** Whether the screen itself has no tab bar — the layout decision. */
  protected readonly layoutWithoutTabs = computed(() =>
    this.hideTabs()
    || (
      this.preferences.experienceMode() === 'practitioner'
      && this.currentPath().startsWith('/m/ask')
    ),
  );

  /**
   * Whether the tab bar is drawn. An open sheet hides the bar (see
   * SheetOverlayService) but must not change the layout: `.content` keeps
   * its bottom padding, so the page behind the scrim does not jump.
   */
  protected readonly tabsSuppressed = computed(() => this.layoutWithoutTabs() || this.overlay.open());

  protected readonly tabs = computed<MobileTab[]>(() => {
    if (this.preferences.experienceMode() === 'practitioner') {
      // Practitioner keeps transits inside Yantra so Calendar remains a primary
      // daily almanac destination instead of competing with chart workbench tools.
      return [
        { commands: ['today'], label: 'Today', icon: 'figma-yantra-nav-sun' },
        { commands: ['chart'], label: 'Yantra', icon: 'figma-yantra-nav-active' },
        { commands: ['chart', 'periods'], label: 'Dashas', icon: 'figma-yantra-nav-clock' },
        { commands: ['calendar'], label: 'Calendar', icon: 'nav-calendar' },
        { commands: ['settings'], label: 'Settings', icon: 'figma-yantra-nav-settings' },
      ];
    }
    // Ask-first with Calendar for every reader. Explore lists the chart and
    // its tools; Settings is the fifth tab, as in Practitioner (Hawk, 2026-10-20).
    return [
      { commands: ['today'], label: 'Today', icon: 'nav-today' },
      { commands: ['ask'], label: 'Ask', icon: 'nav-ask' },
      { commands: ['calendar'], label: 'Calendar', icon: 'nav-calendar' },
      { commands: ['explore'], label: 'Explore', icon: 'nav-explore' },
      { commands: ['settings'], label: 'Settings', icon: 'nav-settings' },
    ];
  });

  protected readonly tabTrack = (_index: number, tab: MobileTab) => tab.commands.join('/');

  protected tabLink(tab: MobileTab): string[] {
    return ['/m', ...tab.commands];
  }

  protected tabActive(tab: MobileTab): boolean {
    const path = this.currentPath();
    const route = `/m/${tab.commands.join('/')}`;
    const mode = this.preferences.experienceMode();

    if (mode !== 'practitioner') {
      if (route === '/m/explore') {
        // Everything reached from Explore keeps Explore lit, so a reader
        // always knows which tab Back will eventually return them to.
        return EXPLORE_ROOTS.some((root) => under(path, root));
      }
      if (route === '/m/settings') {
        return SETTINGS_ROOTS.some((root) => under(path, root));
      }
      return under(path, route);
    }

    if (mode === 'practitioner') {
      if (route === '/m/chart/periods') {
        return path === '/m/chart/periods' || path.startsWith('/m/chart/periods/');
      }
      if (route === '/m/calendar') {
        return path === '/m/calendar' || path.startsWith('/m/calendar/');
      }
      if (route === '/m/chart') {
        return (
          (path === '/m/chart' || path.startsWith('/m/chart/') || path.startsWith('/m/transits')) &&
          !(path === '/m/chart/periods' || path.startsWith('/m/chart/periods/'))
        );
      }
    }

    return path === route || path.startsWith(`${route}/`);
  }

  /**
   * A tab press. On the tab already showing its root, the press scrolls back
   * to the top rather than doing nothing — the router ignores a same-URL
   * navigation, so this is the only feedback the reader would get.
   */
  protected onTabClick(tab: MobileTab): void {
    const route = `/m/${tab.commands.join('/')}`;
    if (this.currentPath() === route) {
      this.haptics.select();
      this.scroller()?.scrollToTop();
      return;
    }
    this.haptics.tap();
  }

  protected retryConnection(): void {
    void this.connectivity.retry();
  }

}
