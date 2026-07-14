import { Component, OnInit, computed, inject, signal } from '@angular/core';
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
import { PreferencesService } from './core/preferences.service';
import { KundliDialogComponent } from './shell/kundli-dialog/kundli-dialog.component';
import { SidebarComponent } from './shell/sidebar/sidebar.component';

@Component({
  selector: 'app-root',
  imports: [
    RouterOutlet,
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
  private prefs = inject(PreferencesService);
  private confirmation = inject(ConfirmationService);
  private messages = inject(MessageService);
  private router = inject(Router);
  protected readonly currentUrl = computed(() => this.url());
  protected readonly profileOptions = computed(() =>
    this.store.kundlis().map((k) => ({
      label: `${k.name} · ${k.relation}`,
      sublabel: `${k.sun_sign || 'Unknown'} · ${k.birth_year}`,
      value: k.id,
    })),
  );
  private readonly url = signal(this.router.url);

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

  protected selectProfile(id: string | null): void {
    if (!id) {
      this.store.activeId.set(null);
      this.router.navigate(['/app']);
      return;
    }
    this.router.navigate(['/kundli', id]);
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
}
