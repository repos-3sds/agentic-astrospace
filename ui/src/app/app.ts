import { Component, HostListener, OnInit, computed, inject, signal } from '@angular/core';
import { A11yModule } from '@angular/cdk/a11y';
import { FormsModule } from '@angular/forms';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { ConfirmDialog } from 'primeng/confirmdialog';
import { Select } from 'primeng/select';
import { Toast } from 'primeng/toast';
import { TooltipModule } from 'primeng/tooltip';
import { filter } from 'rxjs';

import { AuthService } from './core/auth.service';
import { KundliStore } from './core/kundli.store';
import { Kundli } from './core/models';
import { PreferencesService } from './core/preferences.service';
import { ThemeService } from './core/theme.service';
import { KundliDialogComponent } from './shell/kundli-dialog/kundli-dialog.component';
import { ACCOUNT_NAV, GLOBAL_PRIMARY_NAV, KUNDLI_MORE_NAV, PROFILE_PRIMARY_NAV, ROUTE_TITLES } from './shell/mobile-nav';
import { SidebarComponent } from './shell/sidebar/sidebar.component';

const SELECTED_PROFILE_STORAGE_KEY = 'astrospace:selected-profile';

@Component({
  selector: 'app-root',
  imports: [
    RouterOutlet,
    A11yModule,
    FormsModule,
    SidebarComponent,
    KundliDialogComponent,
    LucideAngularModule,
    ButtonModule,
    Select,
    Toast,
    ConfirmDialog,
    TooltipModule,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App implements OnInit {
  protected readonly store = inject(KundliStore);
  protected readonly auth = inject(AuthService);
  protected readonly theme = inject(ThemeService);
  private prefs = inject(PreferencesService);
  private confirmation = inject(ConfirmationService);
  private messages = inject(MessageService);
  private router = inject(Router);
  protected readonly globalPrimaryNav = signal(GLOBAL_PRIMARY_NAV);
  protected readonly profilePrimaryNav = signal(PROFILE_PRIMARY_NAV);
  protected readonly mobilePrimaryNav = computed(() =>
    this.store.activeId() ? this.profilePrimaryNav() : this.globalPrimaryNav(),
  );
  protected readonly moreNav = signal(KUNDLI_MORE_NAV);
  protected readonly accountNav = signal(ACCOUNT_NAV);
  protected readonly moreOpen = signal(false);
  protected readonly profileSheetOpen = signal(false);
  protected readonly profileQuery = signal('');
  private readonly selectedProfileSnapshot = signal<Kundli | null>(this.restoreSelectedProfile());
  protected readonly currentUrl = computed(() => this.url());
  protected readonly profileOptions = computed(() =>
    this.store.kundlis().map((k) => ({
      label: `${k.name} · ${k.relation}`,
      sublabel: `${k.sun_sign || 'Unknown'} · ${k.birth_year}`,
      value: k.id,
    })),
  );
  private readonly url = signal(this.router.url);
  protected readonly currentSection = computed(() => this.sectionFromUrl(this.currentUrl()));
  protected readonly mobileTitle = computed(() => ROUTE_TITLES[this.currentSection()] ?? 'AstroSpace');
  protected readonly inProfileWorkspace = computed(() => this.currentUrl().startsWith('/kundli/'));
  protected readonly mobileProfileLabel = computed(() => {
    const active = this.store.active();
    if (!active) return 'Choose profile';
    const parts = [active.name, active.relation].filter(Boolean);
    return parts.join(' · ');
  });
  protected activeProfileForSheet(): Kundli | null {
    const active = this.store.active();
    if (active) return active;
    const snapshot = this.selectedProfileSnapshot() ?? this.restoreSelectedProfile();
    const browserPath = typeof location === 'undefined' ? '' : location.pathname;
    const id = this.store.activeId() ?? this.profileIdFromUrl(this.currentUrl()) ?? this.profileIdFromUrl(browserPath);
    if (snapshot?.id === id) return snapshot;
    const inWorkspace = this.inProfileWorkspace() || browserPath.startsWith('/kundli/');
    return snapshot && inWorkspace ? snapshot : null;
  }
  protected readonly moreActive = computed(() => {
    const section = this.currentSection();
    const visibleInPrimaryNav = this.mobilePrimaryNav().some((item) => item.route === section);
    return this.moreOpen() || (!visibleInPrimaryNav && this.moreNav().some((item) => item.route === section));
  });
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

  protected readonly title = computed(() => this.store.active()?.name ?? 'AstroSpace');
  protected readonly publicOnly = computed(() => {
    const path = this.currentUrl().split('?')[0].split('#')[0];
    return path === '/' || path.startsWith('/auth');
  });

  protected readonly subtitle = computed(() => {
    const k = this.store.active();
    if (!k) return 'Select or add a kundli to begin';
    const parts = [k.sun_sign, k.relation, `born ${k.birth_year}`].filter(Boolean);
    return parts.join(' · ');
  });

  @HostListener('document:keydown.escape')
  protected closeTopSheet(): void {
    if (this.profileSheetOpen()) {
      this.profileSheetOpen.set(false);
      return;
    }
    if (this.moreOpen()) this.moreOpen.set(false);
  }

  async ngOnInit(): Promise<void> {
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event) => this.url.set(event.urlAfterRedirects));
    try {
      await this.auth.init();
      if (this.auth.isAuthenticated()) {
        if (this.auth.enabled() && this.auth.session()) await this.prefs.syncCloud();
        await this.store.load();
      }
    } catch (e) {
      this.messages.add({
        severity: 'error',
        summary: 'Could not load kundlis',
        detail: (e as Error).message,
      });
    }
  }

  protected edit(): void {
    const active = this.store.active();
    if (active) this.store.openEdit(active);
  }

  protected editProfileFromSheet(profile: { id: string }): void {
    const snapshot = this.selectedProfileSnapshot();
    const active =
      this.store.kundlis().find((item) => item.id === profile.id) ??
      (snapshot?.id === profile.id ? snapshot : null);
    if (!active) return;
    this.profileSheetOpen.set(false);
    this.store.openEdit(active);
  }

  protected editActiveDetails(): void {
    const active = this.activeProfileForSheet();
    if (!active) {
      this.openProfileSheet();
      return;
    }
    this.moreOpen.set(false);
    this.profileSheetOpen.set(false);
    this.editProfileFromSheet(active);
  }

  protected selectProfile(id: string | null): void {
    if (!id) {
      this.store.activeId.set(null);
      this.clearSelectedProfile();
      this.router.navigate(['/app']);
      return;
    }
    const selected = this.store.kundlis().find((profile) => profile.id === id) ?? null;
    if (selected) this.rememberSelectedProfile(selected);
    this.profileSheetOpen.set(false);
    this.moreOpen.set(false);
    this.router.navigate(['/kundli', id]);
  }

  protected openProfileSheet(): void {
    const active = this.store.active();
    if (active) this.rememberSelectedProfile(active);
    this.profileQuery.set('');
    this.moreOpen.set(false);
    this.profileSheetOpen.set(true);
  }

  protected closeProfileSheet(): void {
    this.profileSheetOpen.set(false);
  }

  protected openMore(): void {
    this.profileSheetOpen.set(false);
    this.moreOpen.set(true);
  }

  protected closeMore(): void {
    this.moreOpen.set(false);
  }

  protected goMobile(route: string): void {
    if (route === 'home') {
      this.moreOpen.set(false);
      this.router.navigate(['/app']);
      return;
    }

    if (route === 'profiles') {
      this.openProfileSheet();
      return;
    }

    if (route === 'settings') {
      this.moreOpen.set(false);
      this.router.navigate(['/settings']);
      return;
    }

    const id = this.store.activeId();
    if (!id) {
      this.openProfileSheet();
      return;
    }
    this.moreOpen.set(false);
    this.router.navigate(['/kundli', id, route]);
  }

  protected addProfileFromSheet(): void {
    this.profileSheetOpen.set(false);
    this.moreOpen.set(false);
    this.store.openAdd();
  }

  protected routeActive(route: string): boolean {
    return this.currentSection() === route || (route === 'home' && this.currentSection() === 'home');
  }

  protected goHome(): void {
    this.moreOpen.set(false);
    this.profileSheetOpen.set(false);
    this.store.activeId.set(null);
    this.clearSelectedProfile();
    this.router.navigate(['/app']);
  }

  protected confirmLogout(): void {
    this.moreOpen.set(false);
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

  protected confirmDelete(): void {
    const active = this.store.active();
    if (!active) return;
    this.confirmation.confirm({
      header: 'Delete kundli',
      message: `Delete ${active.name}'s kundli? All readings will be removed too.`,
      acceptButtonProps: { label: 'Delete', severity: 'danger' },
      rejectButtonProps: { label: 'Cancel', severity: 'secondary', outlined: true },
      accept: async () => {
        try {
          await this.store.remove(active.id);
          this.messages.add({ severity: 'success', summary: 'Kundli deleted' });
          this.router.navigate(['/app']);
        } catch (e) {
          this.messages.add({
            severity: 'error',
            summary: 'Delete failed',
            detail: (e as Error).message,
          });
        }
      },
    });
  }

  private sectionFromUrl(url: string): string {
    const path = url.split('?')[0].split('#')[0];
    if (path === '/app') return 'home';
    if (path === '/settings') return 'settings';
    const kundliMatch = path.match(/^\/kundli\/[^/]+(?:\/([^/]+))?/);
    if (kundliMatch) return kundliMatch[1] ?? 'overview';
    return 'home';
  }

  private profileIdFromUrl(url: string): string | null {
    const match = url.split('?')[0].split('#')[0].match(/^\/kundli\/([^/]+)/);
    return match?.[1] ?? null;
  }

  private rememberSelectedProfile(profile: Kundli): void {
    this.selectedProfileSnapshot.set(profile);
    sessionStorage.setItem(SELECTED_PROFILE_STORAGE_KEY, JSON.stringify(profile));
  }

  private clearSelectedProfile(): void {
    this.selectedProfileSnapshot.set(null);
    sessionStorage.removeItem(SELECTED_PROFILE_STORAGE_KEY);
  }

  private restoreSelectedProfile(): Kundli | null {
    try {
      return JSON.parse(sessionStorage.getItem(SELECTED_PROFILE_STORAGE_KEY) || 'null') as Kundli | null;
    } catch {
      return null;
    }
  }
}
