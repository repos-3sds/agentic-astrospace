import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { NotesComponent } from './notes.component';

describe('NotesComponent', () => {
  const activeId = signal<string | null>('p1');
  const active = signal<{ id: string; name: string; relation: string } | null>({ id: 'p1', name: 'Lakshmi', relation: 'self' });

  beforeEach(() => {
    localStorage.removeItem('astrospace.mobile.notes.draft');
    localStorage.removeItem('astrospace.mobile.notes.draft.p1');
    localStorage.removeItem('astrospace.mobile.notes.draft.p2');
    TestBed.configureTestingModule({
      imports: [NotesComponent],
      providers: [provideRouter([]), { provide: KundliStore, useValue: { activeId, active } }],
    });
  });

  afterEach(() => {
    activeId.set('p1');
    active.set({ id: 'p1', name: 'Lakshmi', relation: 'self' });
  });

  it('keeps one note per profile and moves the old shared draft to the first profile (U22)', () => {
    localStorage.setItem('astrospace.mobile.notes.draft', 'old draft');
    const fixture = TestBed.createComponent(NotesComponent);
    fixture.detectChanges();
    const area: HTMLTextAreaElement = fixture.nativeElement.querySelector('textarea');
    expect(area.value).toBe('old draft');
    expect(localStorage.getItem('astrospace.mobile.notes.draft')).toBeNull();
    expect(localStorage.getItem('astrospace.mobile.notes.draft.p1')).toBe('old draft');
    expect(area.getAttribute('spellcheck')).toBe('true');

    activeId.set('p2');
    active.set({ id: 'p2', name: 'Ravi', relation: 'spouse' });
    fixture.detectChanges();
    expect(area.value).toBe('');
    expect(area.getAttribute('aria-label')).toBe('Notes about Ravi');
    area.value = 'about Ravi';
    area.dispatchEvent(new Event('input'));
    expect(localStorage.getItem('astrospace.mobile.notes.draft.p2')).toBe('about Ravi');
    expect(localStorage.getItem('astrospace.mobile.notes.draft.p1')).toBe('old draft');
  });
});
