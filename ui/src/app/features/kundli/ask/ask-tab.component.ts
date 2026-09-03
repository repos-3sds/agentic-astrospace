import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';
import { MobileAskThread, MobileAskThreadService } from '../../mobile/ask/mobile-ask-thread.service';
import { LucideAngularModule } from 'lucide-angular';
import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';
import { ASK_NAVIGATION, AskNavigation } from '../../mobile/ask/ask-navigation';

export function webAskNavigation(): AskNavigation {
  const store = inject(KundliStore);
  return {
    web: true,
    path: (screen) => ['/kundli', store.activeId()!, 'ask', ...(screen ? [screen] : [])],
    chart: () => ['/kundli', store.activeId()!, 'chart'],
  };
}

@Component({
  selector: 'app-ask-tab',
  imports: [RouterLink, RouterLinkActive, RouterOutlet, LucideAngularModule],
  providers: [{ provide: ASK_NAVIGATION, useFactory: webAskNavigation }],
  host: { class: 'as-mobile web-ask' },
  templateUrl: './ask-tab.component.html',
  styleUrl: './ask-tab.component.scss',
})
export class AskTabComponent {
  protected readonly navigation = inject(ASK_NAVIGATION);
  protected readonly preferences = inject(PreferencesService);
  protected readonly ready = signal(false);
  protected readonly loadError = signal(false);
  protected readonly recent = signal<MobileAskThread[]>([]);
  protected readonly recentLoading = signal(false);
  protected readonly recentError = signal(false);
  protected readonly railOpen = signal(false);
  private readonly threads = inject(MobileAskThreadService);
  private readonly router = inject(Router);
  private recentEpoch = 0;
  private readonly store = inject(KundliStore);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);

  constructor() {
    this.router.events.pipe(filter(event => event instanceof NavigationEnd), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => { if (this.ready()) void this.loadRecent(); });
    if (this.route.parent?.paramMap) {
      this.route.parent.paramMap.pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe(() => { void this.loadProfile(); });
    } else {
      void this.loadProfile();
    }
  }

  protected async loadProfile(): Promise<void> {
    this.recentEpoch++;
    this.recent.set([]);
    this.ready.set(false);
    this.loadError.set(false);
    try {
      await this.store.load();
      if (this.destroyRef.destroyed) return;
      const id = this.route.parent?.snapshot.paramMap.get('id');
      if (!id || !this.store.kundlis().some(profile => profile.id === id)) {
        this.loadError.set(true);
        return;
      }
      this.store.setActive(id);
      this.ready.set(true);
      void this.loadRecent();
    } catch {
      if (!this.destroyRef.destroyed) this.loadError.set(true);
    }
  }

  protected async loadRecent(): Promise<void> {
    const id = this.store.activeId();
    if (!id) return;
    const epoch = ++this.recentEpoch;
    this.recentLoading.set(true);
    this.recentError.set(false);
    try {
      const rows = await this.threads.list(id);
      if (epoch !== this.recentEpoch || this.destroyRef.destroyed || this.store.activeId() !== id) return;
      this.recent.set(rows.filter(row => row.kundli_id === id && !row.archived_at).slice(0, 15));
    } catch {
      if (epoch === this.recentEpoch) this.recentError.set(true);
    } finally {
      if (epoch === this.recentEpoch) this.recentLoading.set(false);
    }
  }

  protected setMode(value: string): void {
    if (value === 'guided' || value === 'balanced' || value === 'practitioner') {
      this.preferences.experienceMode.set(value);
    }
  }
}
