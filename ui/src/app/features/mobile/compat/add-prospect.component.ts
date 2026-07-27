import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { inject } from '@angular/core';

@Component({
  selector: 'as-add-prospect',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <a class="mcof-back" [routerLink]="['/m','compat']"><img src="mobile/back.svg" alt="" /><span>Compatibility</span></a>
    <form class="mcof-form" (submit)="submit($event)">
      <header><h1>Add the prospect</h1><p>Just their birth details — no full profile needed.</p></header>
      <label>NAME<span><img src="mobile/field-who.svg" alt="" /><input name="name" value="Ravi" /></span></label>
      <label>DATE OF BIRTH<span><img src="mobile/field-date.svg" alt="" /><input name="date" value="12 March 1994" /></span></label>
      <label>TIME OF BIRTH<span><img src="mobile/field-time.svg" alt="" /><input name="time" [value]="approximate() ? 'Approximate time' : '07:40 AM'" /></span></label>
      <p class="mcof-approx">Don’t know the exact time? <button type="button" (click)="approximate.set(!approximate())">{{ approximate() ? 'Use exact' : 'Use approximate' }}</button></p>
      <label>PLACE OF BIRTH<span><img src="mobile/pin-accent.svg" alt="" /><input name="place" value="Hyderabad, Telangana" /></span></label>
      <button class="mcof-submit" type="submit">Check compatibility</button>
    </form>
  `,
  styleUrl: './add-prospect.component.scss',
})
export class AddProspectComponent {
  private readonly router = inject(Router);
  readonly approximate = signal(false);
  protected submit(event: Event): void { event.preventDefault(); void this.router.navigate(['/m', 'compat', 'results']); }
}
