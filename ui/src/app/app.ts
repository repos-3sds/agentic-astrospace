import { Component, HostListener, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { A11yModule } from '@angular/cdk/a11y';
import { Location } from '@angular/common';
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
import { SheetOverlayService } from './core/sheet-overlay.service';
import { ThemeService } from './core/theme.service';
import { KundliDialogComponent } from './shell/kundli-dialog/kundli-dialog.component';
import { ACCOUNT_NAV, GLOBAL_PRIMARY_NAV, KUNDLI_MORE_GROUPS, PROFILE_PRIMARY_NAV, ROUTE_TITLES } from './shell/mobile-nav';
import { SidebarComponent } from './shell/sidebar/sidebar.component';
import { SplashComponent } from './shell/splash/splash.component';
import { App as CapacitorApp } from '@capacitor/app';
import { Capacitor } from '@capacitor/core';

/**
 * Screens with nowhere in-app to go back to. Capacitor's hardware back
 * button otherwise falls through to the WebView's own history — which
 * includes every `pushState` the SPA ever made, onboarding and the marketing
 * landing page included, so pressing back enough times on the dashboard
 * walked out through sign-in and into the web app's home page. Stopping the
 * unwind here and asking to exit instead is what every native Android app
 * does at its own root; this app just never told Capacitor which routes
 * those are.
 */
const NATIVE_EXIT_ROUTES = ['/m/today', '/m/start'];

const SELECTED_PROFILE_STORAGE_KEY = 'astrospace:selected-profile';
const ANIMATED_SPLASH_FADE_MS = 360;

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
    SplashComponent,
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App implements OnInit, OnDestroy {
  protected readonly store = inject(KundliStore);
  protected readonly auth = inject(AuthService);
  protected readonly theme = inject(ThemeService);
  private prefs = inject(PreferencesService);
  private confirmation = inject(ConfirmationService);
  private messages = inject(MessageService);
  private router = inject(Router);
  private sheetOverlay = inject(SheetOverlayService);
  private location = inject(Location);
  private removeViewportInsetObserver: (() => void) | null = null;
  private removeBackButtonListener: (() => void) | null = null;
  private animatedSplashFadeTimer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    // Native boot starts on a route that does not depend on auth or the network.
    // ngOnInit advances a restored session into the shell once auth resolves.
    // Web is untouched: isNativePlatform() is false in every browser.
    if (Capacitor.isNativePlatform()) {
      const path = this.router.url.split('?')[0];
      if (path === '/' || path === '') {
        void this.router.navigateByUrl('/m/start');
      }
    }
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
  protected readonly showAnimatedSplash = signal(false);
  protected readonly animatedSplashFading = signal(false);
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
  protected readonly mobileTitle = computed(() => ROUTE_TITLES[this.currentSection()] ?? 'SIDDHA');
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

  protected readonly title = computed(() => this.store.active()?.name ?? 'SIDDHA');
  protected readonly publicOnly = computed(() => {
    const path = this.currentUrl().split('?')[0].split('#')[0];
    // /m is the native app shell — it renders its own app bar and tab bar,
    // so the web chrome must not wrap it.
    return path === '/' || path.startsWith('/auth') || path.startsWith('/admin')
      || path.startsWith('/m');
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
    this.removeViewportInsetObserver = this.installViewportInsetObserver();
    this.removeBackButtonListener = this.installBackButtonHandler();
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event) => this.url.set(event.urlAfterRedirects));
    try {
      await this.auth.init();
      if (this.auth.isAuthenticated()) {
        if (
          Capacitor.isNativePlatform()
          && this.router.url.split('?')[0] === '/m/start'
        ) {
          await this.router.navigateByUrl('/m');
        }
        if (this.auth.enabled() && this.auth.session()) await this.prefs.syncCloud();
        await this.store.load();
      }
    } catch (e) {
      this.messages.add({
        severity: 'error',
        summary: 'Could not load kundlis',
        detail: (e as Error).message,
      });
    } finally {
      // In `finally`: a failed session restore still has to uncover the app.
      // Leaving the splash up on error would look like a hang, and the error
      // toast above is already the honest signal.
      await this.hideNativeSplash();
      this.startAnimatedSplashIntro();
    }
  }

  /**
   * Dismiss the native splash once the first screen can paint.
   *
   * `launchAutoHide` is false in capacitor.config.ts, so nothing else will do
   * this — if this method stops being called the app boots to a stuck splash.
   * Imported lazily so the web bundle does not pull in a native-only plugin.
   */
  private async hideNativeSplash(): Promise<void> {
    if (!Capacitor.isNativePlatform()) return;
    try {
      const { SplashScreen } = await import('@capacitor/splash-screen');
      await SplashScreen.hide();
    } catch {
      // Never let splash teardown break boot.
    }
  }

  ngOnDestroy(): void {
    this.removeViewportInsetObserver?.();
    this.removeBackButtonListener?.();
    this.clearAnimatedSplashTimers();
  }

  protected finishAnimatedSplash(): void {
    if (!this.showAnimatedSplash() || this.animatedSplashFading()) return;
    this.animatedSplashFading.set(true);
    this.clearAnimatedSplashTimers();
    this.animatedSplashFadeTimer = setTimeout(() => {
      this.showAnimatedSplash.set(false);
      this.animatedSplashFading.set(false);
      this.animatedSplashFadeTimer = null;
    }, ANIMATED_SPLASH_FADE_MS);
  }

  private startAnimatedSplashIntro(): void {
    if (!Capacitor.isNativePlatform()) return;
    this.showAnimatedSplash.set(true);
    this.animatedSplashFading.set(false);
    this.clearAnimatedSplashTimers();
  }

  private clearAnimatedSplashTimers(): void {
    if (this.animatedSplashFadeTimer) {
      clearTimeout(this.animatedSplashFadeTimer);
      this.animatedSplashFadeTimer = null;
    }
  }

  /**
   * Replace Capacitor's default hardware-back behaviour (which drives the
   * WebView's own history — see NATIVE_EXIT_ROUTES's comment) with one keyed
   * to this app's own idea of where "back" goes.
   */
  private installBackButtonHandler(): () => void {
    if (!Capacitor.isNativePlatform()) return () => undefined;
    let handle: { remove: () => void } | null = null;
    void CapacitorApp.addListener('backButton', () => this.handleBackButton()).then((h) => {
      handle = h;
    });
    return () => handle?.remove();
  }

  private handleBackButton(): void {
    // A sheet is the thing being looked at; close it rather than navigating
    // the route underneath.
    if (this.sheetOverlay.dismissTop()) return;
    const path = this.router.url.split('?')[0];
    if (NATIVE_EXIT_ROUTES.includes(path)) {
      this.confirmExitApp();
      return;
    }
    // Angular's Location, not Capacitor's default — this pops one entry the
    // same way an in-app back affordance would, rather than falling through
    // to the WebView's raw history.
    this.location.back();
  }

  private confirmExitApp(): void {
    this.confirmation.confirm({
      header: 'Exit app',
      message: 'Close the app?',
      acceptButtonProps: { label: 'Exit', severity: 'danger' },
      rejectButtonProps: { label: 'Stay', severity: 'secondary', outlined: true },
      accept: () => {
        void CapacitorApp.exitApp();
      },
    });
  }

  private installViewportInsetObserver(): () => void {
    if (typeof window === 'undefined' || typeof document === 'undefined') return () => undefined;
    if (Capacitor.getPlatform() === 'android') {
      document.documentElement.style.setProperty('--as-native-bottom', '48px');
    }
    const viewport = window.visualViewport;
    if (!viewport) {
      return () => {
        document.documentElement.style.removeProperty('--as-native-bottom');
      };
    }
    let frame = 0;
    const update = () => {
      if (frame) window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => {
        frame = 0;
        const bottomInset = Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop);
        document.documentElement.style.setProperty('--as-visual-bottom', `${Math.round(bottomInset)}px`);
      });
    };
    update();
    viewport.addEventListener('resize', update);
    viewport.addEventListener('scroll', update);
    window.addEventListener('orientationchange', update);
    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      viewport.removeEventListener('resize', update);
      viewport.removeEventListener('scroll', update);
      window.removeEventListener('orientationchange', update);
      document.documentElement.style.removeProperty('--as-native-bottom');
      document.documentElement.style.removeProperty('--as-visual-bottom');
    };
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
}
