import { Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { TooltipModule } from 'primeng/tooltip';

import { AuthService } from '../../core/auth.service';
import { KundliStore } from '../../core/kundli.store';
import { ThemeService } from '../../core/theme.service';

interface NavTab {
  route: string;
  label: string;
  icon: string;
}

const KUNDLI_TABS: NavTab[] = [
  { route: 'overview', label: 'Overview', icon: 'layout-dashboard' },
  { route: 'vedic', label: 'Vedic', icon: 'sparkles' },
  { route: 'varga-charts', label: 'Varga Charts', icon: 'boxes' },
  { route: 'dashas', label: 'Dashas', icon: 'calendar-clock' },
  { route: 'transits', label: 'Transits', icon: 'radar' },
  { route: 'calendar', label: 'Calendar', icon: 'calendar-days' },
  { route: 'ashtakavarga', label: 'Ashtakavarga', icon: 'grid-3x3' },
  { route: 'yogas-doshas', label: 'Yogas & Doshas', icon: 'badge-alert' },
  { route: 'chart', label: 'Chart', icon: 'chart-no-axes-combined' },
  { route: 'readings', label: 'Readings', icon: 'book-open-check' },
  { route: 'compat', label: 'Compatibility', icon: 'heart-handshake' },
  { route: 'notes', label: 'Notes', icon: 'notebook-tabs' },
];

const AI_TAB: NavTab = { route: 'ask', label: 'Ask AI', icon: 'sparkles' };

@Component({
  selector: 'app-sidebar',
  imports: [
    FormsModule,
    RouterLink,
    RouterLinkActive,
    LucideAngularModule,
    ButtonModule,
    TooltipModule,
  ],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss',
})
export class SidebarComponent {
  protected readonly store = inject(KundliStore);
  protected readonly theme = inject(ThemeService);
  private auth = inject(AuthService);
  private confirmation = inject(ConfirmationService);
  private messages = inject(MessageService);
  private router = inject(Router);

  protected readonly collapsed = signal(localStorage.getItem('astrospace-sidebar') === 'collapsed');
  protected readonly profileOverlayOpen = signal(false);
  protected readonly profileQuery = signal('');
  protected readonly tabs = KUNDLI_TABS;
  protected readonly aiTab = AI_TAB;
  protected readonly toggleLabel = computed(() =>
    this.collapsed() ? 'Expand sidebar' : 'Collapse sidebar',
  );
  protected readonly filteredProfiles = computed(() => {
    const q = this.profileQuery().trim().toLowerCase();
    if (!q) return this.store.kundlis();
    return this.store.kundlis().filter((k) =>
      [
        k.name,
        k.relation,
        k.sun_sign,
        k.moon_sign,
        k.ascendant,
        k.birth_city,
        String(k.birth_year),
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(q)),
    );
  });

  constructor() {
    effect(() => {
      localStorage.setItem('astrospace-sidebar', this.collapsed() ? 'collapsed' : 'expanded');
    });
  }

  protected toggle(): void {
    this.collapsed.update((value) => !value);
  }

  protected goHome(): void {
    this.store.activeId.set(null);
    this.router.navigate(['/app']);
  }

  protected tabLink(route: string): string[] {
    const id = this.store.activeId();
    return id ? ['/kundli', id, route] : ['/app'];
  }

  protected openProfileOverlay(): void {
    this.profileQuery.set('');
    this.profileOverlayOpen.set(true);
  }

  protected closeProfileOverlay(): void {
    this.profileOverlayOpen.set(false);
  }

  protected selectProfile(id: string): void {
    this.store.activeId.set(id);
    this.profileOverlayOpen.set(false);
    this.router.navigate(['/kundli', id]);
  }

  protected addProfile(): void {
    this.profileOverlayOpen.set(false);
    this.store.openAdd();
  }

  protected confirmLogout(): void {
    this.confirmation.confirm({
      header: 'Log out',
      message: 'End this AstroSpace session on this device?',
      acceptButtonProps: { label: 'Log out', severity: 'danger' },
      rejectButtonProps: { label: 'Cancel', severity: 'secondary', outlined: true },
      accept: async () => {
        await this.auth.signOut();
        this.store.kundlis.set([]);
        this.store.activeId.set(null);
        this.messages.add({ severity: 'success', summary: 'Logged out' });
        this.router.navigate(['/']);
      },
    });
  }
}
