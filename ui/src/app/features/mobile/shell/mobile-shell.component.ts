import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import {
  NavigationEnd,
  Router,
  RouterLink,
  RouterLinkActive,
  RouterOutlet,
} from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map, startWith } from 'rxjs';
import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';

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
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './mobile-shell.component.html',
  styleUrl: './mobile-shell.component.scss',
  host: { class: 'as-mobile' },
})
export class MobileShellComponent {
  private readonly router = inject(Router);
  private readonly kundlis = inject(KundliStore);
  protected readonly preferences = inject(PreferencesService);

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

  protected readonly tabs = computed(() => {
    const fixed = [
      { commands: ['today'], label: 'Today', icon: 'nav-today' },
    ];
    const more = { commands: ['settings'], label: 'More', icon: 'nav-more' };
    if (this.preferences.experienceMode() === 'guided') {
      return [
        ...fixed,
        { commands: ['ask'], label: 'Ask', icon: 'nav-ask' },
        { commands: ['remedies'], label: 'What to do', icon: 'nav-chart' },
        { commands: ['calendar'], label: 'Calendar', icon: 'nav-calendar' },
        more,
      ];
    }
    if (this.preferences.experienceMode() === 'practitioner') {
      return [
        ...fixed,
        { commands: ['chart'], label: 'Chart', icon: 'nav-chart' },
        { commands: ['chart', 'periods'], label: 'Periods', icon: 'nav-ask' },
        { commands: ['transits'], label: 'Transits', icon: 'nav-calendar' },
        more,
      ];
    }
    return [
      ...fixed,
      { commands: ['ask'], label: 'Ask', icon: 'nav-ask' },
      { commands: ['chart'], label: 'Chart', icon: 'nav-chart' },
      { commands: ['calendar'], label: 'Calendar', icon: 'nav-calendar' },
      more,
    ] satisfies MobileTab[];
  });

  protected readonly tabTrack = (_index: number, tab: MobileTab) => tab.commands.join('/');

  protected tabLink(tab: MobileTab): string[] {
    return ['/m', ...tab.commands];
  }
}
