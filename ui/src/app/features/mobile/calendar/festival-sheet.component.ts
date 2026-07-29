import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { FestivalOccurrence } from '../../../core/models';
import { SheetComponent } from '../sheet/sheet.component';

@Component({
  selector: 'as-festival-sheet',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SheetComponent],
  template: `
    <as-sheet (dismissed)="dismissed.emit()">
      <header class="mcal-festival-head">
        <span class="mcal-date-tile"><b>{{ dayNumber() }}</b><small>{{ monthShort() }}</small></span>
        <span><h2>{{ festival().name }}</h2><p>{{ dateLabel() }}</p></span>
      </header>
      <p class="mcal-festival-copy">{{ festival().description || 'A traditional Hindu observance computed for the selected place.' }}</p>
      @if (festival().observance_note) {
        <p class="mcal-note">{{ festival().observance_note }}</p>
      }
      <p class="mcal-eyebrow">WHAT TO DO</p>
      <ul class="mcal-prepare">
        @for (item of practiceSteps(); track item) { <li>{{ item }}</li> }
      </ul>
      <p class="mcal-eyebrow">HOW TO DO IT</p>
      <section class="mcal-how">
        @for (item of howSteps(); track item) {
          <p>{{ item }}</p>
        }
      </section>
      <p class="mcal-eyebrow">MANTRA / PRAYER</p>
      <section class="mcal-mantra">
        <b>{{ mantra().title }}</b>
        <p>{{ mantra().detail }}</p>
      </section>
      @if (festival().is_convention_dependent) {
        <p class="mcal-window"><img src="mobile/clock.svg" alt="" aria-hidden="true" />Date may vary by family sampradaya or regional panchangam.</p>
      }
      <button class="mcal-remind" type="button" (click)="reminded = true">{{ reminded ? 'Reminder set' : 'Remind me that morning' }}</button>
    </as-sheet>
  `,
  styleUrl: './festival-sheet.component.scss',
})
export class FestivalSheetComponent {
  readonly festival = input<FestivalOccurrence>(emptyFestival());
  readonly dismissed = output<void>();
  reminded = false;

  protected readonly dayNumber = computed(() => Number(this.festival().occurs_on.slice(8, 10)));
  protected readonly monthShort = computed(() =>
    new Intl.DateTimeFormat('en', { month: 'short' }).format(new Date(`${this.festival().occurs_on}T12:00:00`)),
  );
  protected readonly dateLabel = computed(() =>
    new Intl.DateTimeFormat('en', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date(`${this.festival().occurs_on}T12:00:00`)),
  );
  protected readonly practiceSteps = computed(() => {
    const prep = this.festival().prep_guidance;
    return [
      prep || 'Keep the observance simple: clean the space, light a lamp, and offer prayer according to your family practice.',
      'Choose a morning or evening moment that does not conflict with your household tradition.',
      'Avoid expensive or fear-based remedies; devotion, charity, and steadiness are enough.',
    ];
  });
  protected readonly howSteps = computed(() => {
    const festival = this.festival();
    return [
      festival.observance_note || 'Follow your family or temple convention first when it differs from app guidance.',
      'Keep the observance proportionate: clean space, simple offering, short prayer, and charity if appropriate.',
      'Avoid fear-based purchases or elaborate remedies unless they are already part of your tradition.',
    ];
  });
  protected readonly mantra = computed(() => mantraFor(this.festival()));
}

function emptyFestival(): FestivalOccurrence {
  const today = new Date().toISOString().slice(0, 10);
  return {
    slug: 'festival',
    name: 'Festival details',
    regions: [],
    description: 'Festival guidance will appear once a festival is selected.',
    prep_guidance: null,
    occurs_on: today,
    observance_note: null,
    is_convention_dependent: false,
  };
}

function mantraFor(festival: FestivalOccurrence): { title: string; detail: string } {
  const key = `${festival.slug} ${festival.name}`.toLowerCase();
  if (key.includes('ganesh') || key.includes('vinayaka')) {
    return { title: 'Om Gam Ganapataye Namah', detail: 'Chant gently 11 or 108 times, or simply offer a sincere Ganesha prayer.' };
  }
  if (key.includes('shiva') || key.includes('shivaratri')) {
    return { title: 'Om Namah Shivaya', detail: 'Use quiet japa, abhishekam, or a simple lamp offering according to your tradition.' };
  }
  if (key.includes('krishna') || key.includes('janmashtami')) {
    return { title: 'Om Namo Bhagavate Vasudevaya', detail: 'Chant or listen devotionally; midnight observance varies by tradition.' };
  }
  if (key.includes('rama')) {
    return { title: 'Sri Rama Jaya Rama Jaya Jaya Rama', detail: 'Repeat as nama-japa, or read a short passage from the Ramayana.' };
  }
  if (key.includes('lakshmi') || key.includes('diwali') || key.includes('deepavali')) {
    return { title: 'Om Shreem Mahalakshmyai Namah', detail: 'Keep the prayer sattvic: lamp, gratitude, cleanliness, and charity.' };
  }
  if (key.includes('hanuman')) {
    return { title: 'Om Hanumate Namah', detail: 'Chant with steadiness, or recite/listen to Hanuman Chalisa if that is your practice.' };
  }
  if (key.includes('nag') || key.includes('naga')) {
    return { title: 'Om Namo Bhagavate Vasuki Devaya', detail: 'Offer respect without handling or disturbing living snakes; temple prayer is safest.' };
  }
  if (key.includes('guru')) {
    return { title: 'Guru Vandana', detail: 'Offer gratitude to teachers, elders, and sources of knowledge; a personal prayer is enough.' };
  }
  return { title: 'Simple nama-japa or silent prayer', detail: 'Use the deity/name associated with your family tradition, or sit quietly with a lamp for a few minutes.' };
}
