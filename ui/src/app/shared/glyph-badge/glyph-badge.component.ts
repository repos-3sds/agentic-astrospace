import { Component, computed, input } from '@angular/core';

import { signMeta } from '../../core/glyphs';

@Component({
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
