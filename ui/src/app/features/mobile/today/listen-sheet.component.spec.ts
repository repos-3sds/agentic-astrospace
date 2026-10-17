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
    expect(voice.audioUrl).toHaveBeenCalledWith('నమస్తే Hawk. ఇది మీ reading. రోజును సరళంగా ఉంచండి.');
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
