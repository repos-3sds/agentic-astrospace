import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { KundliStore } from '../../../core/kundli.store';
import { LifeStoryPayload, VedicAll } from '../../../core/models';
import { VedicService } from '../../../core/vedic.service';
import { GuidedStoryComponent } from './guided-story.component';

const chart = {
  meta: { name: 'Ravi' },
  lagna: { sign: 'Gemini', dms: "22°38'29\"", nakshatra: 'Punarvasu', nakshatra_pada: 2 },
  planets: { Moon: { sign: 'Gemini', house: 1, nakshatra: 'Ardra', nakshatra_pada: 2 } },
} as unknown as VedicAll;

const payload: LifeStoryPayload = {
  source: 'agent',
  story: {
    headline: 'A quick, curious mind that fixes hard problems',
    summary: 'You learn by talking and asking. You dig until you find the cause.',
    traits: [
      { title: 'Fast learner', detail: 'You pick things up by talking, reading and asking.' },
      { title: 'Shows what you feel', detail: 'People know where they stand with you.' },
      { title: 'Problem solver', detail: 'You enjoy the hard problems others avoid.' },
      { title: 'Home comes first', detail: 'You put warmth and effort into your family.' },
    ],
    growth: 'A busy mind can run late. Write the worry down, then rest.',
    areas: [
      { key: 'work', title: 'Work & purpose', text: 'Work rewards patience.', tip: 'Note one win a week.', tone: 'gentle' },
      { key: 'relationships', title: 'Relationships', text: 'Closeness grows with time.', tip: 'Say it the same day.', tone: 'steady' },
      { key: 'money', title: 'Money', text: 'Money comes through more than one door.', tip: 'Save first.', tone: 'strong' },
      { key: 'energy', title: 'Energy & routine', text: 'Rest before you are tired.', tip: 'Walk daily.', tone: 'gentle' },
    ],
    chapter: 'You are in a Saturn period until 2039. It puts daily work and solving problems at the front.',
  },
};

describe('GuidedStoryComponent', () => {
  let fixture: ComponentFixture<GuidedStoryComponent>;
  let activeId: ReturnType<typeof signal<string | null>>;
  let story: jasmine.Spy<(id: string) => Promise<LifeStoryPayload>>;

  beforeEach(async () => {
    activeId = signal<string | null>('profile-1');
    story = jasmine.createSpy('story').and.resolveTo(payload);
    await TestBed.configureTestingModule({
      imports: [GuidedStoryComponent],
      providers: [
        provideRouter([]),
        { provide: KundliStore, useValue: { activeId, load: () => Promise.resolve() } },
        { provide: VedicService, useValue: { story, cachedAll: () => chart, all: () => Promise.resolve(chart) } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(GuidedStoryComponent);
  });

  async function settle(): Promise<void> {
    fixture.detectChanges();
    await fixture.whenStable();
    await Promise.resolve();
    fixture.detectChanges();
  }

  it("shows the server's story with personality traits first", async () => {
    await settle();
    expect(story).toHaveBeenCalledWith('profile-1');
    const host = fixture.nativeElement as HTMLElement;
    expect(host.querySelector('.hero h2')?.textContent).toContain('quick, curious mind');
    expect(host.querySelectorAll('.traits li').length).toBe(4);
    expect(host.querySelector('.grow')?.textContent).toContain('Write the worry down');
    expect(host.querySelector('.chapter')?.textContent).toContain('Saturn period until 2039');
  });

  it('labels each area from its tone, and steady carries no badge', async () => {
    await settle();
    const cards = Array.from(fixture.nativeElement.querySelectorAll('.story-card')) as HTMLElement[];
    expect(cards.map((card) => card.querySelector('.badge')?.textContent?.trim() ?? null))
      .toEqual(['Go gently', null, 'Strong', 'Go gently']);
    expect(cards[0].getAttribute('data-tone')).toBe('gentle');
  });

  it('never shows the old fixed badges or chart-source lines', async () => {
    await settle();
    const text = fixture.nativeElement.textContent as string;
    expect(text).not.toContain('Blessed');
    expect(text).not.toContain('Based on');
    expect(text).not.toContain('chart source kept visible');
  });

  it('keeps the birth details on screen while the story is being written', async () => {
    let finish!: (value: LifeStoryPayload) => void;
    story.and.returnValue(new Promise((resolve) => { finish = resolve; }));
    await settle();
    expect(fixture.nativeElement.querySelector('as-birth-details-card')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('.writing')?.textContent).toContain('Writing your story');
    finish(payload);
    await settle();
    expect(fixture.nativeElement.querySelector('.writing')).toBeNull();
    expect(fixture.nativeElement.querySelectorAll('.traits li').length).toBe(4);
  });

  it('renders backup traits that have no title', async () => {
    story.and.resolveTo({
      source: 'template',
      story: { ...payload.story, summary: null, traits: [{ title: null, detail: 'You are lively and adaptable.' }] },
    });
    await settle();
    const item = fixture.nativeElement.querySelector('.traits li') as HTMLElement;
    expect(item.querySelector('b')).toBeNull();
    expect(item.textContent).toContain('lively and adaptable');
  });

  it('asks for birth details when there is no active profile', async () => {
    activeId.set(null);
    await settle();
    expect(story).not.toHaveBeenCalled();
    expect(fixture.nativeElement.querySelector('.story-state a')?.textContent).toContain('Add birth details');
  });
});
