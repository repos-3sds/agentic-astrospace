import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Capacitor } from '@capacitor/core';
import { AuthService } from '../../../core/auth.service';
import { KundliStore } from '../../../core/kundli.store';
import { legalUrl, openLegal } from '../../../core/legal';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { SelectHapticDirective } from '../shared/select-haptic.directive';
import { authErrorMessage, isEmailNotConfirmed, looksLikeEmail } from './auth-error';
import { rememberEmailOptIn } from '../../../core/email-settings.service';

@Component({
  selector: 'as-mobile-auth',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackLinkDirective, FormsModule, RouterLink, SelectHapticDirective],
  templateUrl: './mobile-auth.component.html',
  styleUrl: './mobile-auth.component.scss',
  host: { class: 'as-mobile' },
})
export class MobileAuthComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly kundlis = inject(KundliStore);

  protected readonly mode = signal<'signin' | 'register'>(
    this.route.snapshot.queryParamMap.get('mode') === 'register' ? 'register' : 'signin',
  );
  protected readonly loading = signal(false);
  protected readonly googleLoading = signal(false);
  protected readonly appleLoading = signal(false);
  /** iOS only, and only once the Supabase project has Apple switched on. */
  protected readonly appleAvailable = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly notice = signal<string | null>(null);
  /**
   * The address still waiting for its confirmation link, set after sign-up
   * and when sign-in is refused for it. Shown as one bright callout near the
   * top, because two faint lines above Continue were easy to miss.
   */
  protected readonly confirmEmail = signal<string | null>(null);
  protected readonly resendState = signal<'idle' | 'sending' | 'sent'>('idle');
  protected readonly resendError = signal<string | null>(null);
  /**
   * What an email link did, when it brought the reader here rather than
   * signing them in (AuthService.handleNativeAuthCallback): the address is
   * confirmed but this phone could not finish the sign-in, or the link had
   * expired or was already used.
   */
  protected readonly linkResult = signal<'confirmed' | 'expired' | null>(null);
  protected readonly showPassword = signal(false);
  protected readonly legalUrl = legalUrl;
  protected readonly openLegal = openLegal;
  protected name = '';
  protected email = '';
  protected password = '';
  /**
   * The sign-up email consent. Ticked by default; the reader can untick it
   * here, and every email carries a one-click unsubscribe.
   * Applied at the end of onboarding, once the account exists.
   */
  protected emailOptIn = true;

  /** Register only: carry the consent box across the sign-up redirect. */
  private keepConsent(): void {
    if (this.mode() === 'register') rememberEmailOptIn(this.emailOptIn);
  }

  constructor() {
    // A subscription, not the snapshot: the link can arrive while this
    // screen is already open, waiting for the reader to confirm.
    this.route.queryParamMap.pipe(takeUntilDestroyed()).subscribe((params) => {
      const link = params.get('link');
      if (link !== 'confirmed' && link !== 'expired') return;
      this.mode.set('signin');
      this.error.set(null);
      this.notice.set(null);
      this.showConfirm(null);
      this.linkResult.set(link);
    });
    if (Capacitor.getPlatform() === 'ios') {
      void this.auth.appleSignInEnabled().then((on) => this.appleAvailable.set(on));
    }
  }

  protected setMode(mode: 'signin' | 'register'): void {
    this.mode.set(mode);
    this.error.set(null);
    this.notice.set(null);
    this.showConfirm(null);
    this.linkResult.set(null);
  }

  private showConfirm(email: string | null): void {
    if (email) this.linkResult.set(null);
    this.confirmEmail.set(email);
    this.resendState.set('idle');
    this.resendError.set(null);
  }

  protected async resendConfirmation(): Promise<void> {
    const email = this.confirmEmail();
    if (!email || this.resendState() === 'sending') return;
    this.resendState.set('sending');
    this.resendError.set(null);
    try {
      await this.auth.resendConfirmation(email);
      this.resendState.set('sent');
    } catch (error) {
      this.resendState.set('idle');
      this.resendError.set(authErrorMessage(error, 'We couldn’t send it again. Try in a minute.'));
    }
  }

  protected async submit(): Promise<void> {
    if (!this.email.trim() || !this.password || (this.mode() === 'register' && !this.name.trim())) {
      this.error.set('Complete each field to continue.');
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    this.notice.set(null);
    try {
      // localStorage, not sessionStorage: with email confirmation on, the
      // person leaves the app to confirm and signs in afresh, by which time a
      // session-scoped value is gone and the first profile was named
      // "My chart". Sign-in leaves any stored name alone for the same reason.
      if (this.mode() === 'register') {
        localStorage.setItem('astrospace.onboardingName', this.name.trim());
      }
      this.keepConsent();
      await this.auth.init();
      if (!this.auth.enabled()) {
        this.auth.signedOut.set(false);
        await this.router.navigate(this.mode() === 'signin' ? ['/m', 'today'] : ['/m', 'language']);
      } else if (this.mode() === 'signin') {
        await this.auth.signIn(this.email.trim(), this.password, []);
        this.kundlis.reset();
        await this.kundlis.load();
        await this.router.navigate(
          this.kundlis.kundlis().length ? ['/m', 'today'] : ['/m', 'language'],
        );
      } else {
        await this.auth.signUp(
          this.email.trim(),
          this.password,
          this.name.trim(),
          ['/m', 'language'],
        );
        if (!this.auth.session()) {
          this.mode.set('signin');
          this.showConfirm(this.email.trim());
        }
      }
    } catch (error) {
      if (isEmailNotConfirmed(error)) {
        this.showConfirm(this.email.trim());
      } else {
        this.error.set(authErrorMessage(error));
      }
    } finally {
      this.loading.set(false);
    }
  }

  protected async google(): Promise<void> {
    this.googleLoading.set(true);
    this.error.set(null);
    this.notice.set(null);
    this.keepConsent();
    try {
      await this.auth.init();
      if (!this.auth.enabled()) {
        await this.router.navigate(this.mode() === 'signin' ? ['/m', 'today'] : ['/m', 'language']);
        return;
      }
      await this.auth.signInWithGoogle(
        this.mode() === 'signin' ? '/m/today' : '/m/language',
      );
    } catch (error) {
      this.error.set((error as Error).message || 'Could not open Google sign-in. Try again.');
    } finally {
      this.googleLoading.set(false);
    }
  }

  protected async apple(): Promise<void> {
    this.appleLoading.set(true);
    this.error.set(null);
    this.notice.set(null);
    try {
      await this.auth.signInWithApple(this.mode() === 'signin' ? '/m/today' : '/m/language');
    } catch (error) {
      this.error.set((error as Error).message || 'Could not open Apple sign-in. Try again.');
    } finally {
      this.appleLoading.set(false);
    }
  }

  protected async magicLink(): Promise<void> {
    if (this.loading()) return;
    this.error.set(null);
    this.notice.set(null);
    const email = this.email.trim();
    if (!email) {
      this.error.set('Enter your email first, then request a secure link.');
      return;
    }
    if (!looksLikeEmail(email)) {
      this.error.set('That email address doesn’t look right. Check it and try again.');
      return;
    }
    this.keepConsent();
    this.loading.set(true);
    try {
      await this.auth.init();
      if (this.auth.enabled()) {
        await this.auth.signInWithMagicLink(email, this.mode() === 'signin' ? '/m/today' : '/m/language');
      }
      this.notice.set('Secure link sent. Open it from your email on this device.');
    } catch (error) {
      this.error.set(authErrorMessage(error, 'We couldn’t send the link. Try again in a moment.'));
    } finally {
      this.loading.set(false);
    }
  }

}
