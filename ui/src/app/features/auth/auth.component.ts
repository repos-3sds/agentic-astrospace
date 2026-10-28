import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { PasswordModule } from 'primeng/password';

import { AuthService } from '../../core/auth.service';
import { browserPlatform, openAppHref, openSiddhaApp } from '../../core/open-app';

@Component({
  selector: 'app-auth',
  imports: [FormsModule, LucideAngularModule, ButtonModule, InputTextModule, PasswordModule],
  templateUrl: './auth.component.html',
  styleUrl: './auth.component.scss',
})
export class AuthComponent {
  protected readonly auth = inject(AuthService);
  private router = inject(Router);

  /**
   * This page is the owner's way into the web app; readers belong in the
   * phone app. So there is no sign-up here (an account made in a browser
   * only led to a confirm email and a page that would not let them in), and
   * the first thing a reader sees is a way to open the app.
   */
  protected readonly ownerOnly = inject(ActivatedRoute).snapshot.queryParamMap.get('owner_only') === '1';
  protected readonly platform = browserPlatform();
  protected readonly openAppHref = openAppHref(this.platform);
  protected readonly openSiddhaApp = openSiddhaApp;
  protected email = '';
  protected password = '';
  protected readonly loading = signal(false);
  protected readonly magicLoading = signal(false);
  protected readonly googleLoading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly notice = signal<string | null>(null);

  constructor() {
    this.auth.init().then(() => {
      if (!this.auth.enabled() || this.auth.session()) this.router.navigate(['/app']);
    });
  }

  protected async submit(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    this.notice.set(null);
    try {
      await this.auth.signIn(this.email.trim(), this.password);
    } catch (e) {
      this.error.set((e as Error).message);
    } finally {
      this.loading.set(false);
    }
  }

  protected async sendMagicLink(): Promise<void> {
    const email = this.email.trim();
    if (!email) {
      this.error.set('Enter your email first, then request a magic link.');
      return;
    }
    this.magicLoading.set(true);
    this.error.set(null);
    this.notice.set(null);
    try {
      await this.auth.signInWithMagicLink(email, '/app');
      this.notice.set('Magic link sent. Check your email and open the link on this device.');
    } catch (e) {
      this.error.set((e as Error).message);
    } finally {
      this.magicLoading.set(false);
    }
  }

  protected async signInWithGoogle(): Promise<void> {
    this.googleLoading.set(true);
    this.error.set(null);
    this.notice.set(null);
    try {
      await this.auth.signInWithGoogle('/app');
    } catch (e) {
      this.error.set((e as Error).message);
      this.googleLoading.set(false);
    }
  }
}
