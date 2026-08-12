import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import {
  NavigationEnd,
  Router,
  RouterLink,
  RouterOutlet,
} from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map, startWith } from 'rxjs';
import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';
import { SheetOverlayService } from '../../../core/sheet-overlay.service';
import { HapticsService } from '../../../core/haptics.service';
import {
  TabCelestialFooterComponent,
  tabPlanetForPath,
} from './tab-celestial-footer.component';

interface MobileTab {
  commands: string[];
  label: string;
  icon: string;
}

/**
 * Native app shell: routed content plus the five-tab bar (Figma node 13:66).
 *
 * The shell owns the safe areas. styles.scss has defined --as-safe-* since the
 * mobile UX pass but nothing consumed them, which is why the status bar and
 * home indicator showed as bare white bands in the simulator — the WebView's
 * own background, not the app's.
 */
@Component({
  selector: 'as-mobile-shell',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, RouterLink, TabCelestialFooterComponent],
  templateUrl: './mobile-shell.component.html',
  styleUrl: './mobile-shell.component.scss',
  host: { class: 'as-mobile' },
})
export class MobileShellComponent {
  private readonly router = inject(Router);
  private readonly kundlis = inject(KundliStore);
  protected readonly preferences = inject(PreferencesService);
  protected readonly overlay = inject(SheetOverlayService);
  private readonly haptics = inject(HapticsService);

  constructor() {
    if (!this.kundlis.loaded()) void this.kundlis.load().catch(() => undefined);
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

  protected readonly tabsSuppressed = computed(() =>
    this.hideTabs()
    || this.overlay.open()
    || (
      this.preferences.experienceMode() === 'practitioner'
      && this.currentPath().startsWith('/m/ask')
    ),
  );

  protected readonly tabPlanet = computed(() => tabPlanetForPath(this.currentPath()));

  protected readonly tabs = computed(() => {
    const fixed = [
      { commands: ['today'], label: 'Today', icon: 'nav-today' },
    ];
    if (this.preferences.experienceMode() === 'guided') {
      return [
        ...fixed,
        { commands: ['ask'], label: 'Ask', icon: 'nav-ask' },
        {
          commands: ['explore'],
          label: 'Explore',
          icon: 'nav-check-square',
        },
        { commands: ['calendar'], label: 'Calendar', icon: 'nav-calendar' },
        { commands: ['settings'], label: 'More', icon: 'nav-more' },
      ];
    }
    if (this.preferences.experienceMode() === 'practitioner') {
      // Practitioner keeps transits inside Yantra so Calendar remains a primary
      // daily almanac destination instead of competing with chart workbench tools.
      return [
        { commands: ['today'], label: 'Today', icon: 'figma-yantra-nav-sun' },
        { commands: ['chart'], label: 'Yantra', icon: 'figma-yantra-nav-active' },
        { commands: ['chart', 'periods'], label: 'Dashas', icon: 'figma-yantra-nav-clock' },
        { commands: ['calendar'], label: 'Calendar', icon: 'nav-calendar' },
        { commands: ['settings'], label: 'More', icon: 'figma-yantra-nav-settings' },
      ];
    }
    return [
      ...fixed,
      { commands: ['ask'], label: 'Ask', icon: 'nav-ask' },
      { commands: ['chart'], label: 'Explore', icon: 'nav-check-square' },
      { commands: ['calendar'], label: 'Calendar', icon: 'nav-calendar' },
      { commands: ['settings'], label: 'More', icon: 'nav-more' },
    ] satisfies MobileTab[];
  });

  protected readonly tabTrack = (_index: number, tab: MobileTab) => tab.commands.join('/');

  protected tabLink(tab: MobileTab): string[] {
    return ['/m', ...tab.commands];
  }

  protected tabActive(tab: MobileTab): boolean {
    const path = this.currentPath();
    const route = `/m/${tab.commands.join('/')}`;
    const mode = this.preferences.experienceMode();

    if (mode === 'guided') {
      if (route === '/m/explore') {
        return (
          path === '/m/explore' ||
          path.startsWith('/m/explore/') ||
          path === '/m/chart' ||
          path.startsWith('/m/chart/') ||
          path === '/m/remedies' ||
          path.startsWith('/m/remedies/')
        );
      }
      return path === route || path.startsWith(`${route}/`);
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

  async onTabClick() {
    this.haptics.tap();
  }

}
