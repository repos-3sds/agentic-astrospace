import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

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
  protected readonly tabs = [
    { path: 'today', label: 'Today', icon: 'nav-today' },
    { path: 'ask', label: 'Ask', icon: 'nav-ask' },
    { path: 'chart', label: 'Chart', icon: 'nav-chart' },
    { path: 'calendar', label: 'Calendar', icon: 'nav-calendar' },
    { path: 'more', label: 'More', icon: 'nav-more' },
  ];
}
