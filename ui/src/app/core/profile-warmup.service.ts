import { DestroyRef, Injectable, Injector, effect, inject, untracked } from '@angular/core';

import { ConnectivityService } from './connectivity.service';
import { KundliStore } from './kundli.store';
import { PreferencesService } from './preferences.service';
import { VedicService } from './vedic.service';

/** Let the open profile's own requests go first. */
export const PROFILE_WARMUP_DELAY_MS = 2_500;

/**
 * Keeps every saved profile's day and chart ready, so the profile switcher
 * changes person at once instead of waiting on the network.
 *
 * Until 2026-10-28 only the open profile was ever fetched. Switching to
 * anyone else started from nothing: a skeleton for a round trip at best, and
 * when the API was waking from idle (Cloud Run scales to zero) the 8 s read
 * timeout cut the request off twice and Today showed "Unable to load this
 * view" for a profile that was fine.
 *
 * The others are fetched one at a time, after the open profile's requests,
 * through the same VedicService calls the screens use, so what lands here is
 * exactly what they read from the cache. Anything already cached for today
 * costs nothing. The agent's brief is not warmed: writing one can spend a
 * model call, and Today shows the templated brief until it arrives.
 */
@Injectable({ providedIn: 'root' })
export class ProfileWarmupService {
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  private readonly preferences = inject(PreferencesService);
  private readonly connectivity = inject(ConnectivityService);
  private readonly injector = inject(Injector);
  private timer: ReturnType<typeof setTimeout> | null = null;
  private run = 0;
  private started = false;

  /** Idempotent; the mobile shell calls it once it is up. */
  start(destroyRef: DestroyRef): void {
    if (this.started) return;
    this.started = true;
    const watcher = effect(() => {
      if (!this.kundlis.loaded() || this.connectivity.state() !== 'online') return;
      const ids = this.kundlis.kundlis().map((profile) => profile.id);
      const activeId = this.kundlis.activeId();
      // A new place, ayanamsha or node type is a different day and chart.
      this.preferences.panchangaContextKey();
      this.preferences.ayanamsha();
      this.preferences.nodeType();
      untracked(() => this.schedule(ids, activeId));
    }, { injector: this.injector });
    // A phone left open overnight wakes on a new day with nothing cached for it.
    const onVisible = () => {
      if (document.visibilityState !== 'visible' || !this.kundlis.loaded()) return;
      this.schedule(this.kundlis.kundlis().map((profile) => profile.id), this.kundlis.activeId());
    };
    document.addEventListener('visibilitychange', onVisible);
    destroyRef.onDestroy(() => {
      watcher.destroy();
      document.removeEventListener('visibilitychange', onVisible);
      this.cancel();
      this.started = false;
    });
  }

  private schedule(ids: string[], activeId: string | null): void {
    this.cancel();
    const others = ids.filter((id) => id !== activeId);
    if (!others.length) return;
    const run = this.run;
    this.timer = setTimeout(() => void this.warm(others, run), PROFILE_WARMUP_DELAY_MS);
  }

  private cancel(): void {
    this.run += 1;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
  }

  private async warm(ids: string[], run: number): Promise<void> {
    for (const id of ids) {
      if (run !== this.run || this.connectivity.state() !== 'online') return;
      // Still saved? A profile removed meanwhile is a 404, not a warm-up.
      if (!this.kundlis.kundlis().some((profile) => profile.id === id)) continue;
      await Promise.allSettled([this.vedic.dailyGuidance(id), this.vedic.all(id)]);
    }
  }
}
