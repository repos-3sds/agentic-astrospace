import { DestroyRef, ErrorHandler, Injectable, Injector, inject } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { Capacitor } from '@capacitor/core';
import { filter } from 'rxjs';

import { environment } from '../../environments/environment';
import { PreferencesService } from './preferences.service';

/** The product events worth a funnel. Anything else is a screen view. */
export type AnalyticsEvent =
  | 'onboarding_completed'
  | 'ask_submitted'
  | 'ask_answered'
  | 'ask_referred_out'
  | 'limit_reached'
  | 'plans_viewed'
  | 'purchase_started'
  | 'purchase_completed'
  | 'profile_added'
  | 'profile_switched'
  | 'why_opened'
  | 'why_drilldown'
  | 'calendar_exported';

type Properties = Record<string, string | number | boolean | null>;

interface Queued {
  event: string;
  properties: Properties;
  timestamp: string;
}

const ID_KEY = 'astrospace.analytics.id';
const FLUSH_MS = 10_000;
const MAX_QUEUE = 20;

/**
 * Product analytics and crash reports, both to PostHog (checklist D6),
 * without its SDK.
 *
 * PostHog's capture API is one JSON POST, so the app sends that itself
 * rather than shipping a third-party script into the WebView. That keeps
 * three promises the SDK would make hard to audit:
 *
 * - **Off until configured.** No key in the environment, no requests.
 * - **Anonymous.** The id is a random value made on this device, never the
 *   account id or email. No birth details, question text or answer text is
 *   ever a property; routes are sent with ids stripped.
 * - **The reader's switch wins.** Account & privacy › "Share usage and
 *   crash reports" stops sending at once and drops anything queued.
 *
 * Crashes go as `$exception` events, so they land in PostHog's error
 * tracking next to the screen they happened on.
 */
@Injectable({ providedIn: 'root' })
export class AnalyticsService {
  private readonly preferences = inject(PreferencesService);
  private readonly config = environment.posthog;
  private queue: Queued[] = [];
  private timer: ReturnType<typeof setTimeout> | null = null;
  private distinctId: string | null = null;
  private appVersion: string | null = null;
  private started = false;

  get enabled(): boolean {
    return !!this.config?.key && this.preferences.shareUsage();
  }

  /** Called once at boot: screen views, flush on backgrounding, app version. */
  start(router: Router, destroyRef: DestroyRef): void {
    if (this.started || !this.config?.key) return;
    this.started = true;
    const subscription = router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe((event) => this.screen(event.urlAfterRedirects));
    const onHide = () => { if (document.visibilityState === 'hidden') this.flush(true); };
    document.addEventListener('visibilitychange', onHide);
    destroyRef.onDestroy(() => {
      subscription.unsubscribe();
      document.removeEventListener('visibilitychange', onHide);
    });
    if (Capacitor.isNativePlatform()) {
      void import('@capacitor/app')
        .then(({ App }) => App.getInfo())
        .then((info) => { this.appVersion = `${info.version} (${info.build})`; })
        .catch(() => undefined);
    }
  }

  track(event: AnalyticsEvent, properties: Properties = {}): void {
    this.enqueue(event, properties);
  }

  /** A route with ids and query values removed: `/m/settings/profiles/:id/edit`. */
  screen(url: string): void {
    this.enqueue('$screen', { $screen_name: screenName(url) });
  }

  captureException(error: unknown, handled = false): void {
    const err = error instanceof Error ? error : new Error(typeof error === 'string' ? error : 'Non-error thrown');
    this.enqueue('$exception', {
      $exception_type: err.name,
      $exception_message: scrub(err.message).slice(0, 500),
      $exception_stack_trace_raw: (err.stack ?? '').slice(0, 4000),
      $exception_handled: handled,
      $screen_name: screenName(location.pathname),
    });
    // A crash may be the last thing this session does.
    this.flush(true);
  }

  /** Sends what is queued. `beacon` uses keepalive so it survives the app closing. */
  flush(beacon = false): void {
    if (this.timer) { clearTimeout(this.timer); this.timer = null; }
    if (!this.queue.length) return;
    if (!this.enabled) { this.queue = []; return; }
    const batch = this.queue.splice(0, this.queue.length);
    const host = (this.config!.host || 'https://eu.i.posthog.com').replace(/\/$/, '');
    void fetch(`${host}/batch/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        api_key: this.config!.key,
        batch: batch.map((item) => ({ ...item, properties: { ...item.properties, distinct_id: this.id() } })),
      }),
      keepalive: beacon,
    }).catch(() => undefined); // Analytics never surfaces an error to the reader.
  }

  private enqueue(event: string, properties: Properties): void {
    if (!this.enabled) {
      this.queue = [];
      return;
    }
    this.queue.push({
      event,
      timestamp: new Date().toISOString(),
      properties: {
        ...properties,
        $process_person_profile: false,
        platform: Capacitor.getPlatform(),
        app_version: this.appVersion,
        experience_mode: this.preferences.experienceMode(),
      },
    });
    if (this.queue.length >= MAX_QUEUE) this.flush();
    else if (!this.timer) this.timer = setTimeout(() => this.flush(), FLUSH_MS);
  }

  private id(): string {
    if (this.distinctId) return this.distinctId;
    let id: string | null = null;
    try { id = localStorage.getItem(ID_KEY); } catch { /* storage blocked */ }
    if (!id) {
      id = crypto.randomUUID();
      try { localStorage.setItem(ID_KEY, id); } catch { /* keep it for this session */ }
    }
    return (this.distinctId = id);
  }
}

/** Ids, emails and long numbers out of a path or message before it leaves the phone. */
function scrub(value: string): string {
  return value
    .replace(/[\w.+-]+@[\w-]+\.[\w.-]+/g, ':email')
    .replace(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi, ':id')
    .replace(/\b\d{4,}\b/g, ':n');
}

export function screenName(url: string): string {
  const path = url.split(/[?#]/)[0] || '/';
  return scrub(path).replace(/\/[A-Za-z0-9_-]{20,}(?=\/|$)/g, '/:id');
}

/**
 * Angular's error handler, plus a crash report. The default handler still
 * logs to the console, so nothing about local debugging changes.
 */
@Injectable()
export class ReportingErrorHandler extends ErrorHandler {
  private readonly injector = inject(Injector);

  override handleError(error: unknown): void {
    super.handleError(error);
    try {
      // Resolved lazily: an error thrown while the app is still constructing
      // its services must not fail again here.
      this.injector.get(AnalyticsService).captureException(error);
    } catch {
      // Reporting is best effort.
    }
  }
}
