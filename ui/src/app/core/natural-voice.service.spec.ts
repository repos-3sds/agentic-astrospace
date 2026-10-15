import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { AuthService } from './auth.service';
import { EntitlementService } from './entitlement.service';
import { NaturalVoiceService, naturalChunks } from './natural-voice.service';

describe('naturalChunks', () => {
  it('keeps a section whole when it fits, so intonation never restarts mid-section', () => {
    expect(naturalChunks('Namaste, Hawk.  Here is your reading.')).toEqual([
      'Namaste, Hawk. Here is your reading.',
    ]);
  });

  it('splits long text only at sentence ends, including Telugu danda-free full stops', () => {
    const sentence = 'చంద్రుడు కన్యా రాశిలో ఉన్నాడు.';
    const chunks = naturalChunks(Array(10).fill(sentence).join(' '), 80);
    expect(chunks.length).toBeGreaterThan(1);
    for (const chunk of chunks) {
      expect(chunk.length).toBeLessThanOrEqual(80);
      expect(chunk.endsWith('.')).toBeTrue();
    }
    expect(chunks.join(' ')).toBe(Array(10).fill(sentence).join(' '));
  });

  it('returns nothing for blank text', () => {
    expect(naturalChunks('   ')).toEqual([]);
  });
});

describe('NaturalVoiceService', () => {
  let service: NaturalVoiceService;
  let entitlements: jasmine.SpyObj<EntitlementService>;
  let http: HttpTestingController;

  beforeEach(() => {
    entitlements = jasmine.createSpyObj<EntitlementService>('EntitlementService', ['snapshot']);
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: EntitlementService, useValue: entitlements },
        { provide: AuthService, useValue: { getAccessToken: () => Promise.resolve('token') } },
      ],
    });
    service = TestBed.inject(NaturalVoiceService);
    http = TestBed.inject(HttpTestingController);
  });

  it('is available only when the server grants audio.natural_voice', async () => {
    entitlements.snapshot.and.resolveTo({ entitlements: { 'audio.natural_voice': true } } as never);
    expect(await service.available()).toBeTrue();
  });

  it('is not available on the free plan or when the check fails', async () => {
    entitlements.snapshot.and.resolveTo({ entitlements: { 'audio.natural_voice': false } } as never);
    expect(await service.available()).toBeFalse();

    const fresh = TestBed.runInInjectionContext(() => new NaturalVoiceService());
    entitlements.snapshot.and.rejectWith(new Error('offline'));
    expect(await fresh.available()).toBeFalse();
  });

  it('asks the server for audio with the reader token and lets a failure retry', async () => {
    const text = `Unique test text ${Math.random()}`;
    const first = service.audioUrl(text);
    const request = await waitFor(() => http.match('/api/v1/voice/speech')[0]);
    expect(request.request.body).toEqual({ text, language: 'auto' });
    expect(request.request.headers.get('Authorization')).toBe('Bearer token');
    request.flush(new Blob(['x']), { status: 503, statusText: 'Unavailable' });
    await expectAsync(first).toBeRejected();

    void service.audioUrl(text).catch(() => undefined);
    const retry = await waitFor(() => http.match('/api/v1/voice/speech')[0]);
    expect(retry).toBeTruthy();
    retry.flush(new Blob(['mp3'], { type: 'audio/mpeg' }));
  });
});

async function waitFor<T>(probe: () => T | undefined): Promise<T> {
  for (let i = 0; i < 50; i++) {
    const value = probe();
    if (value) return value;
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
  throw new Error('timed out');
}
