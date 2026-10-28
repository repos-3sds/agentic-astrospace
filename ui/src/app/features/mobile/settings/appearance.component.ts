import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { ThemePreference, ThemeService } from '../../../core/theme.service';
import { BackLinkDirective } from '../../../core/back-link.directive';
import { WidgetBridgeService } from '../../../core/widget-bridge.service';
import { SelectHapticDirective } from '../shared/select-haptic.directive';

interface AppearanceOption {
  id: ThemePreference;
  label: string;
  detail: string;
}

@Component({
  selector: 'as-appearance',
  standalone: true,
  imports: [BackLinkDirective, SelectHapticDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './appearance.component.html',
  styleUrl: './appearance.component.scss',
})
export class AppearanceComponent implements OnInit {
  protected readonly theme = inject(ThemeService);
  protected readonly options: AppearanceOption[] = [
    { id: 'system', label: 'System', detail: 'Follow your device setting' },
    { id: 'light', label: 'Light', detail: 'Warm and bright' },
    { id: 'dark', label: 'Dark', detail: 'Gentle in low light' },
  ];

  protected readonly widgets = inject(WidgetBridgeService);
  /** Card opacity for the home-screen widgets, 0-100; null until the phone answers. */
  protected readonly widgetOpacity = signal<number | null>(null);

  ngOnInit(): void {
    void this.widgets.opacity().then((percent) => this.widgetOpacity.set(percent));
  }

  protected select(preference: ThemePreference): void {
    this.theme.setPreference(preference);
  }

  /** While dragging: move the label and preview only. */
  protected previewOpacity(event: Event): void {
    this.widgetOpacity.set(Number((event.target as HTMLInputElement).value));
  }

  /** On release: store it and redraw the widgets once. */
  protected saveOpacity(event: Event): void {
    const percent = Number((event.target as HTMLInputElement).value);
    this.widgetOpacity.set(percent);
    void this.widgets.setOpacity(percent);
  }
}
