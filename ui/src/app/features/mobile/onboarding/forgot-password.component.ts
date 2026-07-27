import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth.service';

@Component({
  selector: 'as-forgot-password',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './forgot-password.component.html',
  styleUrl: './forgot-password.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'as-mobile' },
})
export class ForgotPasswordComponent {
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);

  protected email = this.route.snapshot.queryParamMap.get('email') ?? '';
  protected readonly loading = signal(false);
  protected readonly sent = signal(false);
  protected readonly error = signal<string | null>(null);

  protected async send(): Promise<void> {
    const email = this.email.trim();
    if (!email) {
      this.error.set('Enter the email registered to your account.');
      return;
    }

    this.loading.set(true);
    this.error.set(null);
    try {
      await this.auth.resetPassword(email, '/m/auth');
      // The same state is shown whether or not an account exists. Supabase also
      // follows this rule, preventing this form from exposing registered users.
      this.sent.set(true);
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }
}
