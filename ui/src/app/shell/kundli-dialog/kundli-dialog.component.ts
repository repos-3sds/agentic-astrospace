import { Component, effect, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import { AutoComplete, AutoCompleteCompleteEvent, AutoCompleteSelectEvent } from 'primeng/autocomplete';
import { ButtonModule } from 'primeng/button';
import { Dialog } from 'primeng/dialog';
import { InputNumberModule } from 'primeng/inputnumber';
import { InputTextModule } from 'primeng/inputtext';
import { Select } from 'primeng/select';
import { TextareaModule } from 'primeng/textarea';

import { KundliStore } from '../../core/kundli.store';
import { KundliPayload, PanchangaCity } from '../../core/models';
import { PanchangaService } from '../../core/panchanga.service';

const RELATIONS = [
  { label: 'Myself', value: 'self' },
  { label: 'Spouse / Partner', value: 'spouse' },
  { label: 'Parent', value: 'parent' },
  { label: 'Sibling', value: 'sibling' },
  { label: 'Child', value: 'child' },
  { label: 'Friend', value: 'friend' },
  { label: 'Colleague', value: 'colleague' },
  { label: 'Other', value: 'other' },
];

@Component({
  selector: 'app-kundli-dialog',
  imports: [
    ReactiveFormsModule,
    AutoComplete,
    Dialog,
    ButtonModule,
    InputTextModule,
    InputNumberModule,
    TextareaModule,
    Select,
  ],
  templateUrl: './kundli-dialog.component.html',
  styleUrl: './kundli-dialog.component.scss',
})
export class KundliDialogComponent {
  protected readonly store = inject(KundliStore);
  private fb = inject(FormBuilder);
  private messages = inject(MessageService);
  private router = inject(Router);

  private panchanga = inject(PanchangaService);

  protected readonly relations = RELATIONS;
  protected readonly saving = signal(false);
  protected readonly citySuggestions = signal<PanchangaCity[]>([]);

  protected form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    relation: ['friend'],
    birth_day: [null as number | null, [Validators.required, Validators.min(1), Validators.max(31)]],
    birth_month: [null as number | null, [Validators.required, Validators.min(1), Validators.max(12)]],
    birth_year: [
      null as number | null,
      [Validators.required, Validators.min(1900), Validators.max(new Date().getFullYear())],
    ],
    birth_hour: [12, [Validators.min(0), Validators.max(23)]],
    birth_minute: [0, [Validators.min(0), Validators.max(59)]],
    birth_city: ['', Validators.required],
    birth_nation: ['IN', [Validators.required, Validators.maxLength(2)]],
    notes: [''],
  });

  // Edge-triggered form reset: only when the dialog transitions closed->open
  // or the edit target changes — never on spurious effect re-runs (PrimeNG
  // overlay interactions inside the modal can re-schedule effects without a
  // dependency change, which used to wipe the form mid-entry).
  private lastResetKey: string | null = null;

  constructor() {
    effect(() => {
      if (!this.store.dialogOpen()) {
        this.lastResetKey = null;
        return;
      }
      const editing = this.store.editing();
      const resetKey = editing ? `edit:${editing.id}` : 'add';
      if (resetKey === this.lastResetKey) return;
      this.lastResetKey = resetKey;
      if (editing) {
        this.form.reset({
          name: editing.name,
          relation: editing.relation || 'friend',
          birth_day: editing.birth_day,
          birth_month: editing.birth_month,
          birth_year: editing.birth_year,
          birth_hour: editing.birth_hour,
          birth_minute: editing.birth_minute,
          birth_city: editing.birth_city,
          birth_nation: editing.birth_nation,
          notes: editing.notes ?? '',
        });
      } else {
        this.form.reset({
          name: '',
          relation: 'friend',
          birth_day: null,
          birth_month: null,
          birth_year: null,
          birth_hour: 12,
          birth_minute: 0,
          birth_city: '',
          birth_nation: 'IN',
          notes: '',
        });
      }
    });
  }

  protected async searchCities(event: AutoCompleteCompleteEvent): Promise<void> {
    const q = event.query?.trim() ?? '';
    if (q.length < 2) {
      this.citySuggestions.set([]);
      return;
    }
    try {
      this.citySuggestions.set(await this.panchanga.cities(q));
    } catch {
      this.citySuggestions.set([]);
    }
  }

  protected onCitySelect(event: AutoCompleteSelectEvent): void {
    const city = event.value as PanchangaCity;
    // The autocomplete sets the control to the selected object; normalize it
    // back to the plain city string and auto-fill the country code.
    this.form.patchValue({
      birth_city: city.city,
      birth_nation: city.nation,
    });
  }

  protected async save(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.messages.add({
        severity: 'warn',
        summary: 'Missing details',
        detail: 'Name, birth date and city are required.',
      });
      return;
    }

    const v = this.form.getRawValue();
    // If the user typed a city without picking a suggestion the control holds
    // a string; if a stray object survived, unwrap it defensively.
    const rawCity = v.birth_city as unknown;
    const cityText = typeof rawCity === 'string' ? rawCity : (rawCity as PanchangaCity)?.city ?? '';
    const payload: KundliPayload = {
      name: v.name.trim(),
      relation: v.relation,
      birth_day: v.birth_day!,
      birth_month: v.birth_month!,
      birth_year: v.birth_year!,
      birth_hour: v.birth_hour ?? 12,
      birth_minute: v.birth_minute ?? 0,
      birth_city: cityText.trim(),
      birth_nation: v.birth_nation.trim().toUpperCase(),
      notes: v.notes.trim(),
    };

    this.saving.set(true);
    try {
      const editing = this.store.editing();
      const saved = editing
        ? await this.store.update(editing.id, payload)
        : await this.store.create(payload);
      this.store.closeDialog();
      this.messages.add({
        severity: 'success',
        summary: editing ? 'Kundli updated' : 'Kundli created',
        detail: saved.name,
      });
      this.router.navigate(['/kundli', saved.id]);
    } catch (e) {
      this.messages.add({
        severity: 'error',
        summary: 'Save failed',
        detail: (e as Error).message,
      });
    } finally {
      this.saving.set(false);
    }
  }
}
