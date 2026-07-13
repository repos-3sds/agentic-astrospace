import { Component, OnInit, computed, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import { ButtonModule } from 'primeng/button';

import { KundliStore } from '../../core/kundli.store';
import { CalendarEvent, CalendarIntelligencePayload, Kundli } from '../../core/models';
import { VedicService } from '../../core/vedic.service';
import { GlyphBadgeComponent } from '../../shared/glyph-badge/glyph-badge.component';
import { SectionCardComponent } from '../../shared/section-card/section-card.component';

interface DashboardInsight {
  kundli: Kundli;
  payload: CalendarIntelligencePayload;
  topEvent: CalendarEvent | null;
  score: number;
}

@Component({
  selector: 'app-dashboard',
  imports: [RouterLink, LucideAngularModule, ButtonModule, GlyphBadgeComponent, SectionCardComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  protected readonly store = inject(KundliStore);
  private vedic = inject(VedicService);

  protected readonly insights = signal<DashboardInsight[]>([]);
  protected readonly insightError = signal<string | null>(null);
  protected readonly insightLoading = signal(false);
  protected readonly recent = computed(() => this.store.kundlis().slice(-4).reverse());
  protected readonly relationCount = computed(
    () => new Set(this.store.kundlis().map((k) => k.relation)).size,
  );
  protected readonly topInsights = computed(() => this.insights().slice(0, 4));
  protected readonly alertCount = computed(
    () => this.insights().filter((row) => row.score >= 75).length,
  );

  constructor() {
    effect(() => {
      const profiles = this.store.kundlis();
      if (!this.store.loaded() || !profiles.length) {
        this.insights.set([]);
        return;
      }
      void this.loadInsights(profiles.slice(0, 8));
    });
  }

  ngOnInit(): void {
    this.store.activeId.set(null);
  }

  private async loadInsights(profiles: Kundli[]): Promise<void> {
    this.insightLoading.set(true);
    this.insightError.set(null);
    try {
      const results = await Promise.allSettled(
        profiles.map(async (kundli) => ({
          kundli,
          payload: await this.vedic.calendarIntelligence(kundli.id, 7),
        })),
      );
      const rows = results
        .flatMap((result) => (result.status === 'fulfilled' ? [result.value] : []))
        .map(({ kundli, payload }) => {
          const todayEvents = payload.by_date[payload.start_date] ?? [];
          const topEvent = [...todayEvents].sort((a, b) => b.strength - a.strength)[0] ?? null;
          const ruleScore = payload.current.active_rules.length ? 82 : 0;
          const transitScore = payload.current.strongest_transit?.strength ?? 0;
          const eventScore = topEvent?.strength ?? 0;
          return {
            kundli,
            payload,
            topEvent,
            score: Math.max(ruleScore, transitScore, eventScore),
          };
        })
        .sort((a, b) => b.score - a.score);
      this.insights.set(rows);
      if (results.some((result) => result.status === 'rejected')) {
        this.insightError.set('Some profiles could not load today intelligence.');
      }
    } catch (e) {
      this.insightError.set((e as Error).message);
      this.insights.set([]);
    } finally {
      this.insightLoading.set(false);
    }
  }

  protected toneClass(event: CalendarEvent | null): string {
    if (!event) return 'neutral';
    if (event.tone === 'supportive') return 'supportive';
    if (event.tone === 'challenging' || event.tone === 'hard') return 'challenging';
    return 'neutral';
  }
}
