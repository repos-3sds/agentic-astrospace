import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/auth.service';
import { KundliStore } from '../../../core/kundli.store';

@Component({
  selector: 'as-mobile-auth',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink],
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
  protected readonly error = signal<string | null>(null);
  protected readonly notice = signal<string | null>(null);
  protected readonly showPassword = signal(false);
  protected name = '';
  protected email = '';
  protected password = '';

  protected setMode(mode: 'signin' | 'register'): void {
    this.mode.set(mode);
    this.error.set(null);
    this.notice.set(null);
  }

  protected async submit(): Promise<void> {
    if (!this.email.trim() || !this.password || (this.mode() === 'register' && !this.name.trim())) {
      this.error.set('Complete each field to continue.');
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    try {
      if (this.mode() === 'register') {
        sessionStorage.setItem('astrospace.onboardingName', this.name.trim());
      } else {
        sessionStorage.removeItem('astrospace.onboardingName');
      }
      await this.auth.init();
      if (!this.auth.enabled()) {
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
          this.notice.set('Check your email to confirm your account, then sign in.');
          this.mode.set('signin');
        }
      }
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  protected async google(): Promise<void> {
    this.googleLoading.set(true);
    this.error.set(null);
    this.notice.set(null);
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

  protected async magicLink(): Promise<void> {
    if (!this.email.trim()) {
      this.error.set('Enter your email first, then request a magic link.');
      return;
    }
    await this.auth.init();
    if (!this.auth.enabled()) {
      this.notice.set('Magic link sent. Check your email.');
      return;
    }
    await this.auth.signInWithMagicLink(
      this.email.trim(),
      this.mode() === 'signin' ? '/m/today' : '/m/language',
    );
    this.notice.set('Magic link sent. Check your email and open it on this device.');
  }

}
