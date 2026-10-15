import { Component, OnDestroy, OnInit, afterNextRender, inject, signal } from '@angular/core';
import { Location } from '@angular/common';
import { Router, RouterOutlet } from '@angular/router';
import { App as CapacitorApp } from '@capacitor/app';
import { Capacitor } from '@capacitor/core';

import { AppBootService } from './core/app-boot.service';
import { NativeKeyboardService } from './core/native-keyboard.service';
import { NavigationHistoryService } from './core/navigation-history.service';
import { SheetOverlayService } from './core/sheet-overlay.service';
import { ThemeService } from './core/theme.service';
import { SplashComponent } from './shell/splash/splash.component';

/**
 * Screens with nowhere in-app to go back to. Capacitor's hardware back
 * button otherwise falls through to the WebView's own history — which
 * includes every `pushState` the SPA ever made, onboarding and the marketing
 * landing page included, so pressing back enough times on the dashboard
 * walked out through sign-in and into the web app's home page. At these
 * roots back sends the app to the background, as every native Android app
 * does at its own root.
 */
const NATIVE_EXIT_ROUTES = ['/m/today', '/m/start'];

const ANIMATED_SPLASH_FADE_MS = 360;

/**
 * The root: a router outlet, the native launch intro, and the native
 * plumbing (back button, insets, keyboard, splash hand-off).
 *
 * Deliberately free of the web app's chrome and of PrimeNG — those live in
 * shell/web-shell, loaded only for routes outside /m. Anything imported here
 * is parsed before the native app's first frame.
 */
@Component({
  selector: 'app-root',
  imports: [RouterOutlet, SplashComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App implements OnInit, OnDestroy {
  protected readonly theme = inject(ThemeService);
  private readonly boot = inject(AppBootService);
  private router = inject(Router);
  private sheetOverlay = inject(SheetOverlayService);
  private location = inject(Location);
  private readonly keyboard = inject(NativeKeyboardService);
  private removeViewportInsetObserver: (() => void) | null = null;
  private removeBackButtonListener: (() => void) | null = null;
  private removeNativeInteractionGuards: (() => void) | null = null;
  private animatedSplashFadeTimer: ReturnType<typeof setTimeout> | null = null;
  private nativeBootReady = false;
  private animatedSplashFinished = false;

  // Eager so in-app history is counted from the first navigation.
  private readonly navigationHistory = inject(NavigationHistoryService);

  protected readonly showAnimatedSplash = signal(false);
  protected readonly animatedSplashFading = signal(false);

  constructor() {
    // Native boot starts on a route that does not depend on auth or the network.
    // ngOnInit advances a restored session into the shell once auth resolves.
    // Web is untouched: isNativePlatform() is false in every browser.
    if (Capacitor.isNativePlatform()) {
      // Angular's overlay must own the first rendered frame. Starting it only
      // after auth.init() allowed /m/start to flash between Android's short
      // system splash and session restoration on a real device.
      this.startAnimatedSplashIntro();
      // The native splash is held (launchAutoHide: false) until the web intro
      // has actually painted, then handed over — same colour, so no flash.
      // Not after boot: boot can wait on the network, and the intro is what
      // covers that wait.
      afterNextRender(() => {
        requestAnimationFrame(() => void this.hideNativeSplash());
      });
      const path = this.router.url.split('?')[0];
      if (path === '/' || path === '') {
        void this.router.navigateByUrl('/m/start');
      }
    }
  }

  async ngOnInit(): Promise<void> {
    this.removeViewportInsetObserver = this.installViewportInsetObserver();
    this.removeBackButtonListener = this.installBackButtonHandler();
    this.removeNativeInteractionGuards = this.installNativeInteractionGuards();
    void this.keyboard.install();
    try {
      await this.boot.run();
    } finally {
      // In `finally`: a failed session restore still has to uncover the app.
      // Leaving the splash up on error would look like a hang, and the boot
      // error the shell reports is already the honest signal. hide() is
      // idempotent; this call is the safety net if the paint hook never ran.
      await this.hideNativeSplash();
      this.nativeBootReady = true;
      this.completeAnimatedSplashIfReady();
    }
  }

  /**
   * Dismiss the native splash.
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
    this.removeNativeInteractionGuards?.();
    this.keyboard.uninstall();
    this.clearAnimatedSplashTimers();
  }

  protected finishAnimatedSplash(): void {
    this.animatedSplashFinished = true;
    this.completeAnimatedSplashIfReady();
  }

  private completeAnimatedSplashIfReady(): void {
    // A tap may skip the animation, but it must never reveal the provisional
    // /m/start route while auth is still deciding between Today and onboarding.
    if (!this.nativeBootReady || !this.animatedSplashFinished) return;
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
    this.animatedSplashFinished = false;
    this.showAnimatedSplash.set(true);
    this.animatedSplashFading.set(false);
    this.clearAnimatedSplashTimers();
  }

  private installNativeInteractionGuards(): () => void {
    if (!Capacitor.isNativePlatform()) return () => undefined;
    document.documentElement.classList.add('as-native-app');
    const preventNativeDrag = (event: Event) => event.preventDefault();
    const preventContextMenu = (event: Event) => {
      const target = event.target as HTMLElement | null;
      if (target?.closest('input, textarea, [contenteditable="true"]')) return;
      event.preventDefault();
    };
    document.addEventListener('dragstart', preventNativeDrag, { capture: true });
    document.addEventListener('contextmenu', preventContextMenu, { capture: true });
    return () => {
      document.documentElement.classList.remove('as-native-app');
      document.removeEventListener('dragstart', preventNativeDrag, { capture: true });
      document.removeEventListener('contextmenu', preventContextMenu, { capture: true });
    };
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
      // Background, not exit: Android's own convention at an app's root, and
      // it keeps the process (and the decrypted cache) warm for the next
      // open. This replaced a PrimeNG "Close the app?" dialog, which was the
      // only reason the native root pulled PrimeNG in at all.
      void CapacitorApp.minimizeApp();
      return;
    }
    // Angular's Location, not Capacitor's default — this pops one entry the
    // same way an in-app back affordance would, rather than falling through
    // to the WebView's raw history.
    this.location.back();
  }

  /**
   * Browser only. In the native app the WebView is resized for the keyboard
   * (see NativeKeyboardService), and real system insets arrive as
   * env(safe-area-inset-*) / --safe-area-inset-* from Capacitor's SystemBars
   * (styles.scss), so there is nothing to measure here.
   */
  private installViewportInsetObserver(): () => void {
    if (typeof window === 'undefined' || typeof document === 'undefined') return () => undefined;
    if (Capacitor.isNativePlatform()) return () => undefined;
    const viewport = window.visualViewport;
    if (!viewport) {
      return () => undefined;
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
      document.documentElement.style.removeProperty('--as-visual-bottom');
    };
  }
}
