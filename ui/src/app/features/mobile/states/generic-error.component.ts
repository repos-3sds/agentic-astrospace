import { ChangeDetectionStrategy, Component, computed, inject, input, output } from '@angular/core';

import { PreferencesService } from '../../../core/preferences.service';

@Component({
  selector: 'as-generic-error',
  standalone: true,
  template: `<div class="error-mark">!</div><h2>{{ title() }}</h2><p>{{ message() }}</p>@if (diagnostic()) {<code>{{ diagnostic() }}</code>}<button type="button" (click)="retried.emit()">Try again</button>`,
  styles: [`:host{display:flex;min-height:100%;box-sizing:border-box;flex-direction:column;align-items:center;justify-content:center;gap:16px;padding:24px;text-align:center;background:var(--m-bg);color:var(--m-text)}.error-mark{width:84px;height:84px;border-radius:50%;display:grid;place-items:center;background:var(--m-bad-soft);color:var(--m-bad);font-size:36px;font-weight:700}h2{font-size:21px;margin:0}p{font-size:15px;line-height:1.52;color:var(--m-muted);margin:0}code{max-width:100%;box-sizing:border-box;padding:10px 12px;border-radius:10px;background:var(--m-surface);color:var(--m-muted);font-size:12px;overflow-wrap:anywhere}button{width:100%;padding:16px;border:0;border-radius:999px;background:var(--m-ink);color:var(--m-on-ink);font-weight:600}`],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GenericErrorComponent {
  private readonly preferences = inject(PreferencesService);
  readonly message = input('We couldn’t reach the guidance service — check your connection and try again.');
  readonly technicalDetail = input('');
  readonly retried = output<void>();
  protected readonly title = computed(() =>
    this.preferences.tone() === 'direct' ? 'Unable to load this view' : 'Let’s try that again',
  );
  protected readonly diagnostic = computed(() =>
    this.preferences.experienceMode() === 'practitioner' ? this.technicalDetail() : '',
  );
}
