import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { SheetComponent } from '../sheet/sheet.component';
import { ManglikException, ManglikPayload } from '../../../core/models';

/**
 * Manglik exception explanation (Figma node 62:140), driven by the engine's
 * own `doshas.manglik` row.
 *
 * The Figma frame shows the "exception met" case. This sheet renders all
 * three outcomes the engine can return — not present, flag weakened by an
 * exception, flag stands — because showing the "cancelled" layout to every
 * user would suppress a flag and invent evidence. A dosha is a flag, not a
 * verdict, in both directions: never escalated, never quietly dropped.
 *
 * The engine never cancels Manglik outright: `net_severity` is one step
 * below `severity` and never below "mild" while any reference is active
 * (`core/vedic/doshas.py::manglik_dosha`). The copy says "weakened", not
 * "cancelled", to match what was actually computed.
 */
@Component({
  selector: 'as-manglik-cancellation-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SheetComponent],
  template: `
    <as-sheet (dismissed)="dismissed.emit()">
      <header class="head">
        <p class="flag" [attr.data-state]="state()">{{ flagLabel() }}</p>
        <h2>{{ headline() }}</h2>
      </header>
      <p class="body">{{ lede() }}</p>

      @if (activeChecks().length) {
        <section class="refs">
          <p class="eyebrow">WHERE MARS SITS</p>
          <ul>
            @for (check of activeChecks(); track check.reference) {
              <li>House {{ check.house }} from {{ check.reference }} ({{ check.reference_sign }})</li>
            }
          </ul>
        </section>
      }

      @for (exception of appliedExceptions(); track exception.rule) {
        <section class="exception applies">
          <h3><img src="mobile/cancellation-check.svg" alt="" aria-hidden="true" />Exception met: {{ exception.rule }}</h3>
          <p>{{ exception.detail }}</p>
        </section>
      }
      @if (state() !== 'not-present' && otherExceptions().length) {
        <section class="exception">
          <h3>{{ appliedExceptions().length ? 'Also checked' : 'Exceptions checked — none applies' }}</h3>
          <ul>
            @for (exception of otherExceptions(); track exception.rule) {
              <li><b>{{ exception.rule }}.</b> {{ exception.detail }}</li>
            }
          </ul>
        </section>
      }

      <p class="eyebrow">WHAT THIS MEANS FOR YOU</p>
      <p class="body">{{ meaning() }}</p>
      @if (conventionNote(); as note) {
        <p class="note">{{ note }}</p>
      }
      @if (sourceLabel(); as source) {
        <p class="source">{{ source }}</p>
      }
      <button class="got-it" type="button" (click)="dismissed.emit()">Got it</button>
    </as-sheet>
  `,
  styleUrl: './manglik-cancellation-sheet.component.scss',
})
export class ManglikCancellationSheetComponent {
  readonly manglik = input.required<ManglikPayload>();
  readonly dismissed = output<void>();

  readonly appliedExceptions = computed<ManglikException[]>(
    () => (this.manglik().exceptions ?? []).filter((row) => row.applies),
  );
  readonly otherExceptions = computed<ManglikException[]>(
    () => (this.manglik().exceptions ?? []).filter((row) => !row.applies),
  );
  readonly activeChecks = computed(() => (this.manglik().checks ?? []).filter((row) => row.active));

  readonly state = computed<'not-present' | 'weakened' | 'stands'>(() => {
    if (!this.manglik().active) return 'not-present';
    return this.appliedExceptions().length ? 'weakened' : 'stands';
  });

  readonly flagLabel = computed(() => {
    const row = this.manglik();
    switch (this.state()) {
      case 'not-present': return 'MARRIAGE · NOT PRESENT';
      case 'weakened': return `MARRIAGE · FLAG, WEAKENED TO ${(row.net_severity ?? row.severity).toUpperCase()}`;
      default: return `MARRIAGE · FLAG, ${row.severity.toUpperCase()}`;
    }
  });

  readonly headline = computed(() => {
    switch (this.state()) {
      case 'not-present': return 'No Manglik flag in this chart';
      case 'weakened': return 'Why your Manglik flag is weakened';
      default: return 'Why this Manglik flag stands';
    }
  });

  readonly lede = computed(() => {
    const row = this.manglik();
    const mars = row.checks?.[0]?.mars_sign;
    const where = mars ? `Mars is in ${mars}. ` : '';
    switch (this.state()) {
      case 'not-present':
        return `${where}It does not fall in houses 1, 2, 4, 7, 8 or 12 from your Lagna, Moon or Venus, so the classical Manglik rule is not triggered.`;
      case 'weakened':
        return `${where}It sits in a house traditionally flagged as Manglik, but classical rules also recognize exceptions — and your chart meets ${this.appliedExceptions().length === 1 ? 'one of them' : 'more than one'}.`;
      default:
        return `${where}It sits in a house traditionally flagged as Manglik, and none of the classical exceptions the engine checks applies here.`;
    }
  });

  readonly meaning = computed(() => {
    switch (this.state()) {
      case 'not-present':
        return 'There is nothing to weigh here for matchmaking. If someone has told you otherwise, ask them which reference point and rule they used — conventions differ.';
      case 'weakened':
        return 'Most practitioners would weigh this placement lightly. The flag is kept, one step softer, rather than removed: mention it to your family astrologer, but it is not something to be anxious about.';
      default:
        return 'This is a flag to discuss, not a verdict on marriage. Traditions differ on how much weight it carries and on which exceptions count, so raise it with a practitioner you trust rather than treating it as settled.';
    }
  });

  readonly conventionNote = computed(() => {
    // With no flag there is nothing an exception could weaken; the engine's
    // note about exception rules would only read as noise here.
    if (this.state() === 'not-present') return null;
    const note = this.manglik().notes?.find((row) => row.toLowerCase().includes('convention'));
    return note ?? (this.manglik().source_status === 'convention_dependent'
      ? 'Which exceptions count, and how much they soften the flag, is convention-dependent.'
      : null);
  });

  readonly sourceLabel = computed(() => {
    const refs = this.manglik().source_refs;
    if (refs?.length) return refs.map((row) => `${row.source}: ${row.detail}`).join(' · ');
    return this.manglik().source_status ? `Source status: ${this.manglik().source_status!.replaceAll('_', ' ')}` : null;
  });
}
