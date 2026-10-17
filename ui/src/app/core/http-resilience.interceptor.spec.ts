import { HttpClient, HttpHeaders, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed, fakeAsync, tick } from '@angular/core/testing';

import {
  API_COMPUTE_GET_TIMEOUT_MS,
  API_GET_RETRY_DELAY_MS,
  API_GET_TIMEOUT_MS,
  API_SLOW_GET_TIMEOUT_MS,
  httpResilienceInterceptor,
} from './http-resilience.interceptor';

describe('httpResilienceInterceptor', () => {
  let http: HttpClient;
  let backend: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([httpResilienceInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    backend = TestBed.inject(HttpTestingController);
  });

  afterEach(() => backend.verify());

  it('retries an API read once after a gateway error', fakeAsync(() => {
    let body: unknown;
    http.get('/api/v1/kundlis').subscribe((value) => (body = value));

    backend.expectOne('/api/v1/kundlis').flush('down', { status: 503, statusText: 'Unavailable' });
    tick(API_GET_RETRY_DELAY_MS);
    backend.expectOne('/api/v1/kundlis').flush([{ id: 'k1' }]);

    expect(body).toEqual([{ id: 'k1' }]);
  }));

  it('gives up after one retry', fakeAsync(() => {
    let status: number | undefined;
    http.get('/api/v1/kundlis').subscribe({ error: (e) => (status = e.status) });

    backend.expectOne('/api/v1/kundlis').flush('down', { status: 502, statusText: 'Bad gateway' });
    tick(API_GET_RETRY_DELAY_MS);
    backend.expectOne('/api/v1/kundlis').flush('down', { status: 502, statusText: 'Bad gateway' });

    expect(status).toBe(502);
  }));

  it('times out a stalled read as 408 and retries it', fakeAsync(() => {
    let status: number | undefined;
    http.get('https://api.example.test/api/v1/settings').subscribe({ error: (e) => (status = e.status) });

    const first = backend.expectOne('https://api.example.test/api/v1/settings');
    tick(API_GET_TIMEOUT_MS);
    expect(first.cancelled).toBeTrue();
    tick(API_GET_RETRY_DELAY_MS);
    const second = backend.expectOne('https://api.example.test/api/v1/settings');
    tick(API_GET_TIMEOUT_MS);
    expect(second.cancelled).toBeTrue();

    expect(status).toBe(408);
  }));

  it('does not retry a client error', fakeAsync(() => {
    let status: number | undefined;
    http.get('/api/v1/kundlis/x').subscribe({ error: (e) => (status = e.status) });

    backend.expectOne('/api/v1/kundlis/x').flush('missing', { status: 404, statusText: 'Not found' });
    tick(API_GET_RETRY_DELAY_MS);
    backend.expectNone('/api/v1/kundlis/x');

    expect(status).toBe(404);
  }));

  it('never retries a write', fakeAsync(() => {
    http.post('/api/v1/kundlis', {}).subscribe({ error: () => undefined });

    backend.expectOne('/api/v1/kundlis').flush('down', { status: 503, statusText: 'Unavailable' });
    tick(API_GET_RETRY_DELAY_MS + API_GET_TIMEOUT_MS);
    backend.expectNone('/api/v1/kundlis');
  }));

  it('leaves streams alone: no timeout on a long answer', fakeAsync(() => {
    let done = false;
    http
      .get('/api/v1/events', { headers: new HttpHeaders({ Accept: 'text/event-stream' }) })
      .subscribe(() => (done = true));

    const req = backend.expectOne('/api/v1/events');
    tick(API_GET_TIMEOUT_MS * 3);
    expect(req.cancelled).toBeFalse();
    req.flush('ok');
    expect(done).toBeTrue();
  }));

  it('leaves non-API requests alone', fakeAsync(() => {
    http.get('/assets/i18n/en.json').subscribe({ error: () => undefined });

    const req = backend.expectOne('/assets/i18n/en.json');
    tick(API_GET_TIMEOUT_MS * 2);
    expect(req.cancelled).toBeFalse();
    req.flush('down', { status: 503, statusText: 'Unavailable' });
    tick(API_GET_RETRY_DELAY_MS);
    backend.expectNone('/assets/i18n/en.json');
  }));

  it('gives the daily brief time to be written instead of cutting it off at 8 s', fakeAsync(() => {
    let body: unknown;
    http.get('/api/v1/context/k/daily/brief?tone=gentle').subscribe((value) => (body = value));
    tick(API_GET_TIMEOUT_MS + 30_000);
    const request = backend.expectOne('/api/v1/context/k/daily/brief?tone=gentle');
    request.flush({ source: 'agent' });
    expect(body).toEqual({ source: 'agent' });
    expect(API_SLOW_GET_TIMEOUT_MS).toBeGreaterThan(120_000);
  }));

  for (const url of [
    '/api/v1/muhurta/k?goal=start_venture&date_from=2026-10-17',
    '/api/v1/vedic/k/calendar-intelligence?days=45',
    '/api/v1/festivals/upcoming?city=Kakinada&days=31',
  ]) {
    it(`lets ${url.split('?')[0]} compute past 8 s`, fakeAsync(() => {
      let body: unknown;
      http.get(url).subscribe((value) => (body = value));
      tick(API_GET_TIMEOUT_MS + 10_000);
      backend.expectOne(url).flush({ ok: true });
      expect(body).toEqual({ ok: true });
    }));
  }

  it('still cuts off a computing read that never answers', fakeAsync(() => {
    let failed: unknown;
    http.get('/api/v1/muhurta/k?goal=general').subscribe({ error: (e) => (failed = e) });
    backend.expectOne('/api/v1/muhurta/k?goal=general');
    tick(API_COMPUTE_GET_TIMEOUT_MS + API_GET_RETRY_DELAY_MS);
    backend.expectOne('/api/v1/muhurta/k?goal=general');
    tick(API_COMPUTE_GET_TIMEOUT_MS);
    expect(failed).toBeTruthy();
  }));

  it('keeps the 8 s limit for the muhurta goal list', fakeAsync(() => {
    let failed: unknown;
    http.get('/api/v1/muhurta/goals').subscribe({ error: (e) => (failed = e) });
    backend.expectOne('/api/v1/muhurta/goals');
    tick(API_GET_TIMEOUT_MS + API_GET_RETRY_DELAY_MS);
    backend.expectOne('/api/v1/muhurta/goals');
    tick(API_GET_TIMEOUT_MS);
    expect(failed).toBeTruthy();
  }));
});
