import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { NgTemplateOutlet } from '@angular/common';
import { RouterLink } from '@angular/router';
import { YogaLearningSheetComponent } from './yoga-learning-sheet.component';
import { Combination, buildCombinations } from './combinations';
import { KundliStore } from '../../../core/kundli.store';
import { YogasDoshasPayload } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { PreferencesService } from '../../../core/preferences.service';
import { GenericErrorComponent } from '../states/generic-error.component';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { SelectHapticDirective } from '../shared/select-haptic.directive';
import { PlanGateService } from '../../../core/plan-gate.service';
import { PlanLockComponent } from '../shared/plan-lock.component';

type Filter = 'all' | 'strengths' | 'flags';

/**
 * Yogas & Doshas (Figma node 41:87), redesigned 2026-10-29 so every card
 * says what the yoga or dosha is, why this chart has it (the placements),
 * and, one tap in, what it can mean, what to do and what to avoid.
 * Flags (doshas and caution yogas) are shown in full on every plan.
 */
@Component({
  selector: 'as-yogas-doshas',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [NgTemplateOutlet, PlanLockComponent, BackLinkDirective, GenericErrorComponent, RouterLink, YogaLearningSheetComponent, SelectHapticDirective],
  templateUrl: './yogas-doshas.component.html',
  styleUrl: './yogas-doshas.component.scss',
})
export class YogasDoshasComponent {
  protected readonly gate = inject(PlanGateService);
  private readonly kundlis = inject(KundliStore);
  private readonly vedic = inject(VedicService);
  private readonly preferences = inject(PreferencesService);
  readonly filter = signal<Filter>('all');
  readonly selected = signal<Combination | null>(null);
  protected readonly data = signal<YogasDoshasPayload | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly mode = computed(() => this.preferences.experienceMode());
  protected readonly practitioner = computed(() => this.mode() === 'practitioner');
  /** Free shows the first two strengths; Plus shows every one. Flags show on every plan. */
  protected readonly allYogas = computed(() => this.gate.allows('yogas.full'));
  protected readonly view = computed(() => buildCombinations(this.data(), this.mode(), this.allYogas()));
  protected readonly showStrengths = computed(() => this.filter() !== 'flags');
  protected readonly showFlags = computed(() => this.filter() !== 'strengths');
  protected readonly filters: { id: Filter; label: string }[] = [
    { id: 'all', label: 'All' },
    { id: 'strengths', label: 'Strengths' },
    { id: 'flags', label: 'Flags' },
  ];

  constructor() {
    effect(() => {
      const activeId = this.kundlis.activeId();
      void this.load(activeId);
    });
  }

  protected open(item: Combination): void {
    this.selected.set(item);
  }

  protected retry(): void {
    void this.load(this.kundlis.activeId());
  }

  private async load(expectedActiveId: string | null): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.kundlis.load();
      const activeId = this.kundlis.activeId();
      if (expectedActiveId && activeId !== expectedActiveId) return;
      if (!activeId) {
        this.data.set(null);
        return;
      }
      this.data.set(await this.vedic.yogasDoshas(activeId));
    } catch (error) {
      this.error.set((error as Error).message);
    } finally {
      this.loading.set(false);
    }
  }
}
