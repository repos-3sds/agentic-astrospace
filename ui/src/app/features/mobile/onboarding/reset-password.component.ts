import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth.service';

@Component({
  selector: 'as-reset-password',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './reset-password.component.html',
  styleUrl: './forgot-password.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'as-mobile' },
})
export class ResetPasswordComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  protected password = '';
  protected confirmation = '';
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);

  protected async save(): Promise<void> {
    if (this.password.length < 8) {
      this.error.set('Use at least 8 characters.');
      return;
    }
    if (this.password !== this.confirmation) {
      this.error.set('The passwords do not match.');
      return;
    }

    this.loading.set(true);
    this.error.set(null);
    try {
      await this.auth.updatePassword(this.password);
      await this.router.navigateByUrl('/m/today');
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }
}
