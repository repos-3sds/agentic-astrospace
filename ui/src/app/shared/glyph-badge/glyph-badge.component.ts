import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { signMeta } from '../../core/glyphs';

@Component({
  // Signal inputs only, so OnPush is safe; the mobile chart screens render these (audit I16).
  changeDetection: ChangeDetectionStrategy.OnPush,
  selector: 'app-glyph-badge',
  imports: [],
  templateUrl: './glyph-badge.component.html',
  styleUrl: './glyph-badge.component.scss',
})
export class GlyphBadgeComponent {
  sign = input<string | null>();
  size = input<number>(40);

  meta = computed(() => signMeta(this.sign()));
}
