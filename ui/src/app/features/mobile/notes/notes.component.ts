import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { KundliStore } from '../../../core/kundli.store';
import { USER_LOCAL_STORAGE_KEYS } from '../../../core/session-teardown';

// The single draft every profile shared before 2026-10-18. It moves to the
// first profile opened, then goes. Per-profile keys share its prefix, so
// SessionTeardown clears them on sign-out and account deletion.
const LEGACY_KEY = USER_LOCAL_STORAGE_KEYS[0];
const keyFor = (profileId: string) => `${LEGACY_KEY}.${profileId}`;

function read(key: string): string | null {
  try { return localStorage.getItem(key); } catch { return null; }
}

function write(key: string, value: string | null): void {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    // Storage can be unavailable (private mode); the text stays for this visit.
  }
}

/**
 * Private notes, one per profile (U22). They stay on this phone: the copy
 * says so plainly, and the export in Account & privacy includes them.
 * Syncing and dated entries are in the deferred backlog.
 */
@Component({
  selector: 'as-mobile-notes',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BackLinkDirective],
  template: `
    <header class="mnote-top"><a [asBack]="['/m','explore']"><img src="mobile/back.svg" alt="" /><span>Explore</span></a><em>On this phone</em></header>
    <main class="mnote-body">
      <header><h1>Notes</h1><p>{{ subtitle() }}</p></header>
      <textarea
        maxlength="2000"
        [value]="text()"
        (input)="update($event)"
        [attr.aria-label]="'Notes about ' + who()"
        placeholder="Write anything you want to remember: a reading, a question, how a day went."
        autocapitalize="sentences"
        spellcheck="true"
      ></textarea>
      <div class="mnote-meta"><span>Saved on this phone</span><span>{{ text().length }} / 2000</span></div>
      <p class="mnote-private"><img src="mobile/info.svg" alt="" aria-hidden="true" /><span>Only you can see these notes. They aren't sent to <span class="siddha-brand">Siddha</span> or used in your readings, and they aren't backed up, so they won't move to a new phone.</span></p>
    </main>
  `,
  styleUrl: './notes.component.scss',
})
export class NotesComponent {
  private readonly store = inject(KundliStore);
  protected readonly who = computed(() => {
    const active = this.store.active();
    return !active || active.relation === 'self' ? 'you' : active.name;
  });
  protected readonly subtitle = computed(() =>
    this.who() === 'you' ? 'Your private notes.' : `Your private notes about ${this.who()}.`);
  readonly text = signal('');
  private key: string | null = null;

  constructor() {
    effect(() => {
      const id = this.store.activeId();
      this.key = id ? keyFor(id) : LEGACY_KEY;
      let value = read(this.key);
      const legacy = id ? read(LEGACY_KEY) : null;
      if (id && value === null && legacy !== null) {
        value = legacy;
        write(this.key, legacy);
        write(LEGACY_KEY, null);
      }
      this.text.set(value ?? '');
    });
  }

  protected update(event: Event): void {
    const value = (event.target as HTMLTextAreaElement).value;
    this.text.set(value);
    if (this.key) write(this.key, value);
  }
}
