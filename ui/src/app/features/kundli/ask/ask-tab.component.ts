import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
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
  const route = inject(ActivatedRoute);
  const standalone = route.snapshot?.routeConfig?.path === 'ask/:id';
  return {
    web: true,
    path: (screen) => standalone
      ? ['/ask', store.activeId()!, ...(screen ? [screen] : [])]
      : ['/kundli', store.activeId()!, 'ask', ...(screen ? [screen] : [])],
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
  protected readonly store = inject(KundliStore);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly threads = inject(MobileAskThreadService);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly navigation = inject(ASK_NAVIGATION);
  protected readonly preferences = inject(PreferencesService);
  protected readonly ready = signal(false);
  protected readonly loadError = signal(false);
  protected readonly recent = signal<MobileAskThread[]>([]);
  protected readonly recentLoading = signal(false);
  protected readonly recentError = signal(false);
  protected readonly railOpen = signal(false);
  protected readonly activeProfile = computed(() => this.store.active());
  protected readonly standalone = this.route.snapshot?.routeConfig?.path === 'ask/:id';
  private recentEpoch = 0;

  constructor() {
    this.router.events.pipe(filter(event => event instanceof NavigationEnd), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => { if (this.ready()) void this.loadRecent(); });
    const profileParams = this.standalone ? this.route.paramMap : this.route.parent?.paramMap;
    if (profileParams) profileParams.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => { void this.loadProfile(); });
    else void this.loadProfile();
  }

  private profileId(): string | null {
    return this.standalone
      ? this.route.snapshot.paramMap.get('id')
      : this.route.parent?.snapshot.paramMap.get('id') ?? null;
  }

  protected async loadProfile(): Promise<void> {
    this.recentEpoch++;
    this.recent.set([]);
    this.ready.set(false);
    this.loadError.set(false);
    try {
      await this.store.load();
      if (this.destroyRef.destroyed) return;
      const id = this.profileId();
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

  protected switchProfile(id: string): void {
    if (!id || id === this.store.activeId()) return;
    void this.router.navigate(['/ask', id]);
  }
}
