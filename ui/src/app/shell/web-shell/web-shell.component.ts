import { Component, HostListener, OnDestroy, computed, effect, inject, signal } from '@angular/core';
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
import { Subscription, filter } from 'rxjs';

import { AppBootService } from '../../core/app-boot.service';
import { AuthService } from '../../core/auth.service';
import { KundliStore } from '../../core/kundli.store';
import { Kundli } from '../../core/models';
import { ThemeService } from '../../core/theme.service';
import { KundliDialogComponent } from '../kundli-dialog/kundli-dialog.component';
import { ACCOUNT_NAV, GLOBAL_PRIMARY_NAV, KUNDLI_MORE_GROUPS, PROFILE_PRIMARY_NAV, ROUTE_TITLES } from '../mobile-nav';
import { SidebarComponent } from '../sidebar/sidebar.component';

const SELECTED_PROFILE_STORAGE_KEY = 'astrospace:selected-profile';

/**
 * The responsive web app's chrome: sidebar, top bar, bottom nav, profile and
 * More sheets, the kundli dialog, and PrimeNG's toast and confirm dialog.
 *
 * Until 2026-10-15 all of this lived in the root component, so every launch
 * of the native app parsed PrimeNG (~520 KB, 40% of the initial bundle) for
 * screens under /m that never use it. It is now one lazy chunk, loaded by
 * web-shell.routes.ts for every route outside /m, with PrimeNG configured by
 * that route's environment injector instead of a global providePrimeNG.
 */
@Component({
  selector: 'app-web-shell',
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
  templateUrl: './web-shell.component.html',
  styleUrl: './web-shell.component.scss',
})
export class WebShellComponent implements OnDestroy {
  protected readonly store = inject(KundliStore);
  protected readonly auth = inject(AuthService);
  protected readonly theme = inject(ThemeService);
  private readonly boot = inject(AppBootService);
  private confirmation = inject(ConfirmationService);
  private messages = inject(MessageService);
  private router = inject(Router);
  private readonly routerEvents: Subscription;

  constructor() {
    this.routerEvents = this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event) => this.url.set(event.urlAfterRedirects));
    // Boot runs in the root component, which no longer carries PrimeNG; the
    // web app's way of saying it failed is still this toast.
    effect(() => {
      const error = this.boot.error();
      if (!error) return;
      const browserPath = typeof window === 'undefined' ? '' : window.location.pathname;
      if (this.isMobileOnboardingRoute(this.router.url) || this.isMobileOnboardingRoute(browserPath)) return;
      this.messages.add({ severity: 'error', summary: 'Could not load kundlis', detail: error });
    });
  }

  ngOnDestroy(): void {
    this.routerEvents.unsubscribe();
  }

  protected readonly globalPrimaryNav = signal(GLOBAL_PRIMARY_NAV);
  protected readonly profilePrimaryNav = signal(PROFILE_PRIMARY_NAV);
  protected readonly mobilePrimaryNav = computed(() =>
    this.store.activeId() ? this.profilePrimaryNav() : this.globalPrimaryNav(),
  );
  protected readonly moreNavGroups = signal(KUNDLI_MORE_GROUPS);
  protected readonly moreNavItems = computed(() => this.moreNavGroups().flatMap((group) => group.items));
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
  protected readonly mobileTitle = computed(() => ROUTE_TITLES[this.currentSection()] ?? 'Siddha');
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
  protected moreActive(): boolean {
    const section = this.visibleSection();
    const visibleInPrimaryNav = this.mobilePrimaryNav().some((item) => item.route === section);
    return this.moreOpen() || (!visibleInPrimaryNav && this.moreNavItems().some((item) => item.route === section));
  }
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

  protected readonly title = computed(() => this.store.active()?.name ?? 'Siddha');
  protected readonly publicOnly = computed(() => {
    const path = this.currentUrl().split('?')[0].split('#')[0];
    // Landing, sign-in, admin and the full-screen Ask render without the web
    // chrome. (/m never reaches this component; app.routes.ts sends it to the
    // native shell before the web shell is loaded.)
    return path === '/' || path.startsWith('/auth') || path.startsWith('/admin')
      || path.startsWith('/ask/');
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
      void this.navigateMobile(['/app']);
      return;
    }
    const selected = this.store.kundlis().find((profile) => profile.id === id) ?? null;
    if (selected) this.rememberSelectedProfile(selected);
    this.profileSheetOpen.set(false);
    this.moreOpen.set(false);
    void this.navigateMobile(['/kundli', id]);
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
      void this.navigateMobile(['/app']);
      return;
    }

    if (route === 'profiles') {
      this.openProfileSheet();
      return;
    }

    if (route === 'settings') {
      this.moreOpen.set(false);
      void this.navigateMobile(['/settings']);
      return;
    }

    const id = this.store.activeId();
    if (!id) {
      this.openProfileSheet();
      return;
    }
    this.moreOpen.set(false);
    void this.navigateMobile(['/kundli', id, route]);
  }

  protected addProfileFromSheet(): void {
    this.profileSheetOpen.set(false);
    this.moreOpen.set(false);
    this.store.openAdd();
  }

  protected routeActive(route: string): boolean {
    const section = this.visibleSection();
    return section === route || (route === 'home' && section === 'home');
  }

  protected goHome(): void {
    this.moreOpen.set(false);
    this.profileSheetOpen.set(false);
    this.store.activeId.set(null);
    this.clearSelectedProfile();
    void this.navigateMobile(['/app']);
  }

  protected confirmLogout(): void {
    this.moreOpen.set(false);
    this.confirmation.confirm({
      header: 'Log out',
      message: 'End this session on this device?',
      acceptButtonProps: { label: 'Log out', severity: 'danger' },
      rejectButtonProps: { label: 'Cancel', severity: 'secondary', outlined: true },
      accept: async () => {
        await this.auth.signOut();
        this.store.kundlis.set([]);
        this.store.activeId.set(null);
        this.messages.add({ severity: 'success', summary: 'Logged out' });
        void this.navigateMobile(['/']);
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
          void this.navigateMobile(['/app']);
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

  private browserPath(): string {
    return typeof location === 'undefined' ? '' : location.pathname;
  }

  private visibleSection(): string {
    const currentUrl = this.currentUrl();
    return this.sectionFromUrl(this.browserPath() || currentUrl);
  }

  private async navigateMobile(commands: unknown[]): Promise<void> {
    this.url.set(this.router.serializeUrl(this.router.createUrlTree(commands)));
    await this.router.navigate(commands);
    this.url.set(this.router.url);
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

  private isMobileOnboardingRoute(url: string): boolean {
    const path = url.split('?')[0].split('#')[0];
    return [
      '/m/start',
      '/m/auth',
      '/m/forgot-password',
      '/m/reset-password',
      '/m/language',
      '/m/welcome',
      '/m/disclaimers',
      '/m/persona',
      '/m/customize',
      '/m/birth-details',
      '/m/insight',
    ].includes(path);
  }
}
