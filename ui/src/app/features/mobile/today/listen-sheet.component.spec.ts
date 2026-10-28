import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { MobileTtsService } from '../../../core/mobile-tts.service';
import { NaturalVoiceService } from '../../../core/natural-voice.service';
import { ListenSheetComponent } from './listen-sheet.component';

const SECTIONS = [
  { label: 'Opening', text: 'Namaste, Hawk. Here is your reading.' },
  { label: 'Close', text: 'Let the day stay simple.' },
];
const TELUGU_SECTIONS = [
  { label: 'Opening', text: 'నమస్తే Hawk. ఇది మీ reading.' },
  { label: 'Close', text: 'రోజును సరళంగా ఉంచండి.' },
];

describe('ListenSheetComponent languages', () => {
  let voice: jasmine.SpyObj<NaturalVoiceService>;

  async function render(natural: boolean) {
    voice = jasmine.createSpyObj<NaturalVoiceService>('NaturalVoiceService', ['available', 'audioUrl', 'telugu']);
    voice.available.and.resolveTo(natural);
    voice.audioUrl.and.resolveTo('blob:audio');
    // The sheet translates in the background once natural voice is on; tests
    // that care resolve this themselves.
    voice.telugu.and.returnValue(new Promise(() => undefined));
    TestBed.configureTestingModule({
      imports: [ListenSheetComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: NaturalVoiceService, useValue: voice },
        {
          provide: MobileTtsService,
          useValue: { nativeAvailable: () => false, stop: () => Promise.resolve(), listVoices: () => Promise.resolve([]) },
        },
      ],
    });
    const fixture = TestBed.createComponent(ListenSheetComponent);
    fixture.componentRef.setInput('title', 'Your day');
    fixture.componentRef.setInput('sections', SECTIONS);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    return fixture;
  }

  function teluguChip(fixture: { nativeElement: HTMLElement }): HTMLButtonElement {
    return [...fixture.nativeElement.querySelectorAll<HTMLButtonElement>('button.lang')].find(
      (button) => button.textContent?.trim() === 'తెలుగు',
    )!;
  }

  it('keeps Telugu off with the phone voice, which has no Telugu text to read', async () => {
    const fixture = await render(false);
    expect(teluguChip(fixture).disabled).toBeTrue();
  });

  it('reads the Telugu rendering of the brief once Telugu is chosen', async () => {
    const fixture = await render(true);
    voice.telugu.and.resolveTo(TELUGU_SECTIONS);
    const changed: string[] = [];
    fixture.componentInstance.languageChanged.subscribe((label) => changed.push(label));

    const chip = teluguChip(fixture);
    expect(chip.disabled).toBeFalse();
    chip.click();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(voice.telugu).toHaveBeenCalledWith(SECTIONS);
    expect(changed).toEqual(['తెలుగు']);
    expect(teluguChip(fixture).getAttribute('aria-pressed')).toBe('true');
    expect(voice.audioUrl).toHaveBeenCalledWith('నమస్తే Hawk. ఇది మీ reading.');
  });

  it('stays in English when the Telugu text cannot be had', async () => {
    const fixture = await render(true);
    voice.telugu.and.rejectWith(new Error('503'));
    teluguChip(fixture).click();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(teluguChip(fixture).getAttribute('aria-pressed')).toBe('false');
    expect(fixture.nativeElement.textContent).toContain('Telugu is unavailable right now');
  });
});

describe('ListenSheetComponent sections and voice', () => {
  const BRIEF = [
    { label: 'Opening', text: 'Namaste, Deepak. Here is your day.' },
    { label: 'Overview', text: 'The Moon brings clear thinking for reviews.' },
    { label: 'Today', text: 'Handle routine work and stay calm.' },
    { label: 'Why', text: 'Your Tarabala is steady today.' },
    { label: 'Close', text: 'Let the day stay simple.' },
  ];
  let voice: jasmine.SpyObj<NaturalVoiceService>;
  let played: string[];

  /** Stands in for the audio element; headless Chrome can't decode the made-up URLs. */
  class FakeAudio {
    src = '';
    paused = true;
    currentTime = 0;
    playbackRate = 1;
    onended: (() => void) | null = null;
    onerror: (() => void) | null = null;
    play(): Promise<void> {
      played.push(decodeURIComponent(this.src.replace('blob:', '')));
      this.paused = false;
      this.currentTime = 1;
      return Promise.resolve();
    }
    pause(): void {
      this.paused = true;
    }
  }

  const RealAudio = window.Audio;
  afterEach(() => (window.Audio = RealAudio));

  async function render(available: Promise<boolean>) {
    played = [];
    (window as unknown as { Audio: unknown }).Audio = FakeAudio;
    voice = jasmine.createSpyObj<NaturalVoiceService>('NaturalVoiceService', ['available', 'audioUrl', 'telugu']);
    voice.available.and.returnValue(available);
    voice.audioUrl.and.callFake((text: string) => Promise.resolve(`blob:${encodeURIComponent(text)}`));
    voice.telugu.and.returnValue(new Promise(() => undefined));
    TestBed.configureTestingModule({
      imports: [ListenSheetComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: NaturalVoiceService, useValue: voice },
        {
          provide: MobileTtsService,
          useValue: { nativeAvailable: () => false, stop: () => Promise.resolve(), listVoices: () => Promise.resolve([]) },
        },
      ],
    });
    const fixture = TestBed.createComponent(ListenSheetComponent);
    fixture.componentRef.setInput('title', 'Your day');
    fixture.componentRef.setInput('sections', BRIEF);
    fixture.detectChanges();
    await settle(fixture);
    return fixture;
  }

  async function settle(fixture: { detectChanges: () => void }) {
    for (let i = 0; i < 5; i++) await new Promise((resolve) => setTimeout(resolve));
    fixture.detectChanges();
  }

  function chip(fixture: { nativeElement: HTMLElement }, label: string): HTMLButtonElement {
    return [...fixture.nativeElement.querySelectorAll<HTMLButtonElement>('button.chapter')].find(
      (button) => button.textContent?.trim() === label,
    )!;
  }

  function playButton(fixture: { nativeElement: HTMLElement }): HTMLButtonElement {
    return fixture.nativeElement.querySelector('button.play')!;
  }

  it('plays the section a chip names, in the natural voice', async () => {
    const fixture = await render(Promise.resolve(true));
    chip(fixture, 'Why').click();
    await settle(fixture);

    expect(played.at(-1)).toBe('Your Tara bala is steady today.');
    expect(chip(fixture, 'Why').getAttribute('aria-pressed')).toBe('true');
    expect(fixture.nativeElement.textContent).toContain('Now playing: Why · Natural voice');
  });

  it('plays the chosen section after a pause, still in the natural voice', async () => {
    const fixture = await render(Promise.resolve(true));
    playButton(fixture).click();
    await settle(fixture);
    playButton(fixture).click(); // pause
    await settle(fixture);
    chip(fixture, 'Close').click();
    await settle(fixture);

    expect(played).toEqual(['Namaste, Deepak. Here is your day.', 'Let the day stay simple.']);
    expect(fixture.nativeElement.textContent).toContain('Now playing: Close · Natural voice');
  });

  it('resumes the same part after a pause rather than starting over', async () => {
    const fixture = await render(Promise.resolve(true));
    chip(fixture, 'Today').click();
    await settle(fixture);
    playButton(fixture).click(); // pause
    await settle(fixture);
    playButton(fixture).click(); // resume
    await settle(fixture);

    expect(played).toEqual(['Handle routine work and stay calm.', 'Handle routine work and stay calm.']);
    expect(voice.audioUrl).toHaveBeenCalledTimes(3); // first-piece prefetch, Today, the piece after it
    expect(fixture.nativeElement.textContent).toContain('Now playing: Today · Natural voice');
  });

  it('keeps the voice it started with when the plan check answers late', async () => {
    let answer!: (ok: boolean) => void;
    const fixture = await render(new Promise<boolean>((resolve) => (answer = resolve)));
    spyOn(window.speechSynthesis, 'speak').and.stub();
    jasmine.clock().install();
    try {
      playButton(fixture).click();
      jasmine.clock().tick(3100); // past the wait: reads in the phone voice
    } finally {
      jasmine.clock().uninstall();
    }
    await settle(fixture);
    answer(true);
    await settle(fixture);

    expect(fixture.nativeElement.textContent).toContain('Phone voice');
    expect(voice.audioUrl).not.toHaveBeenCalled();
  });

  it('does not switch to the phone voice when a later part fails to load', async () => {
    const fixture = await render(Promise.resolve(true));
    playButton(fixture).click();
    await settle(fixture);

    voice.audioUrl.and.rejectWith(new Error('offline'));
    chip(fixture, 'Today').click();
    await settle(fixture);

    expect(fixture.nativeElement.textContent).toContain('Natural voice');
    expect(fixture.nativeElement.textContent).toContain('Couldn’t load the next part');
  });
});
