import { Directive, ElementRef, HostListener, inject } from '@angular/core';
import { HapticsService } from '../../../core/haptics.service';

const CHOICE = 'button, [role="tab"], [role="radio"], [role="option"]';
const SELECTED_CLASSES = ['on', 'is-on', 'active', 'is-active', 'selected', 'is-selected'];

/**
 * A selection haptic for a group of choices — a segmented control, a row of
 * filter chips, a radio list.
 *
 * Put it on the group, not on each segment: one attribute covers every
 * choice inside, including ones rendered by @for. It buzzes only when the
 * tap changes the choice, so tapping the segment already selected stays
 * quiet. Disabled choices never buzz.
 *
 * `select()` is the haptic for a changed choice (see HapticsService), and is
 * a no-op on the web and when the reader turned haptics off.
 */
@Directive({
  selector: '[asSelectHaptic]',
  standalone: true,
})
export class SelectHapticDirective {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;
  private readonly haptics = inject(HapticsService);

  // This runs after the choice's own (click) handler, but before change
  // detection writes the new selected state to the DOM, so the attributes
  // read here are still the state the tap started from.
  @HostListener('click', ['$event'])
  onClick(event: Event): void {
    const target = event.target as HTMLElement | null;
    const choice = target?.closest<HTMLElement>(CHOICE);
    if (!choice || !this.host.contains(choice)) return;
    if (choice.matches(':disabled') || choice.getAttribute('aria-disabled') === 'true') return;
    if (isSelected(choice)) return;
    this.haptics.select();
  }
}

export function isSelected(el: HTMLElement): boolean {
  for (const attr of ['aria-pressed', 'aria-selected', 'aria-checked']) {
    if (el.getAttribute(attr) === 'true') return true;
  }
  return SELECTED_CLASSES.some((name) => el.classList.contains(name));
}
