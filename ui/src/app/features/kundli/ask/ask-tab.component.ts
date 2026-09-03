import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink, RouterOutlet } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';
import { ASK_NAVIGATION, AskNavigation } from '../../mobile/ask/ask-navigation';

export function webAskNavigation(): AskNavigation {
  const store = inject(KundliStore);
  return {
    path: (screen) => ['/kundli', store.activeId()!, 'ask', ...(screen ? [screen] : [])],
    chart: () => ['/kundli', store.activeId()!, 'chart'],
  };
}

@Component({
  selector: 'app-ask-tab',
  imports: [RouterLink, RouterOutlet, LucideAngularModule],
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
  private readonly store = inject(KundliStore);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);

  constructor() {
    if (this.route.parent?.paramMap) {
      this.route.parent.paramMap.pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe(() => { void this.loadProfile(); });
    } else {
      void this.loadProfile();
    }
  }

  protected async loadProfile(): Promise<void> {
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
    } catch {
      if (!this.destroyRef.destroyed) this.loadError.set(true);
    }
  }

  protected setMode(value: string): void {
    if (value === 'guided' || value === 'balanced' || value === 'practitioner') {
      this.preferences.experienceMode.set(value);
    }
  }
}
