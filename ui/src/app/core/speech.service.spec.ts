import { TestBed } from '@angular/core/testing';
import { SpeechService } from './speech.service';

class FakeRecognition {
  static instances: FakeRecognition[] = [];
  lang = '';
  interimResults = false;
  continuous = false;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null = null;
  onerror: ((event: { error: string }) => void) | null = null;
  onend: (() => void) | null = null;
  started = 0;
  stopped = 0;
  constructor() { FakeRecognition.instances.push(this); }
  start(): void { this.started += 1; }
  stop(): void { this.stopped += 1; this.onend?.(); }
  abort(): void { this.stop(); }
}

describe('SpeechService (browser recogniser)', () => {
  const w = window as unknown as Record<string, unknown>;
  let original: unknown;

  beforeEach(() => {
    original = w['SpeechRecognition'];
    FakeRecognition.instances = [];
    w['SpeechRecognition'] = FakeRecognition;
    TestBed.resetTestingModule();
  });

  afterEach(() => {
    if (original === undefined) delete w['SpeechRecognition'];
    else w['SpeechRecognition'] = original;
  });

  it('reports support when the browser exposes a recogniser', () => {
    expect(TestBed.inject(SpeechService).supported()).toBeTrue();
  });

  it('reports no support when no recogniser exists, so the mic can hide', () => {
    delete w['SpeechRecognition'];
    delete w['webkitSpeechRecognition'];
    expect(TestBed.inject(SpeechService).supported()).toBeFalse();
  });

  it('listens in the locale of the Ask response language and publishes partial text', async () => {
    const service = TestBed.inject(SpeechService);
    await service.start('te');
    const recognition = FakeRecognition.instances[0];
    expect(recognition.lang).toBe('te-IN');
    expect(recognition.interimResults).toBeTrue();
    expect(service.listening()).toBeTrue();
    recognition.onresult?.({ results: [[{ transcript: 'Is this a good ' }], [{ transcript: 'time to move' }]] });
    expect(service.transcript()).toBe('Is this a good time to move');
    await service.stop();
    expect(recognition.stopped).toBe(1);
    expect(service.listening()).toBeFalse();
    expect(service.transcript()).toBe('Is this a good time to move');
  });

  it('turns a refused microphone into a readable error', async () => {
    const service = TestBed.inject(SpeechService);
    await service.start('en');
    FakeRecognition.instances[0].onerror?.({ error: 'not-allowed' });
    expect(service.error()).toContain('Microphone access was refused');
  });
});
