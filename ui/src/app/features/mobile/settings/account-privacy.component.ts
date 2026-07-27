import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

/**
 * Settings — Account & privacy (Figma node 69:180).
 *
 * "Export my data" comes first, above sign-out and delete. Data you cannot take
 * with you is not yours, and putting export at the top is the cheapest way to
 * mean the Welcome screen's "your birth details stay yours".
 *
 * Delete is separated by a rule, outlined rather than filled, and carries its
 * consequence in text beneath it. It is deliberately **not wired**: the design
 * has no confirmation step, and an irreversible action that destroys charts,
 * notes and history should not be one tap from a settings list. Wiring it needs
 * a confirm — that is a design question, not something to invent here.
 */
@Component({
  selector: 'as-settings-account',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  templateUrl: './account-privacy.component.html',
  styleUrl: './account-privacy.component.scss',
})
export class AccountPrivacyComponent {
  protected readonly actions = [
    { id: 'export', label: 'Export my data' },
    { id: 'email', label: 'Change email' },
    { id: 'signout', label: 'Sign out' },
  ];
}
