import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { apiUrl } from './api-origin';
import { AuthService } from './auth.service';
import { ConnectivityService } from './connectivity.service';
import { EntitlementService } from './entitlement.service';

const ENTITLEMENT = 'audio.natural_voice';
const ENTITLEMENT_TTL_MS = 10 * 60 * 1000;
const CACHE_NAME = 'natural-voice-v1';
const CACHE_MAX_ENTRIES = 80;
/**
 * Stored in the voiceName preference when the reader picks Siddha's natural
 * voice. "Automatic" (null) also uses it when the plan includes it; naming a
 * phone voice opts out.
 */
export const NATURAL_VOICE_NAME = 'siddha:natural';
/** Kept below the server's per-request byte cap even for Telugu (3 bytes/char). */
export const NATURAL_CHUNK_MAX_CHARS = 1200;

/**
 * Server-made read-aloud audio for Plus readers (Google Chirp 3 HD).
 *
 * Everything here fails soft: `available()` is false and `audioUrl()` throws
 * whenever natural voice can't be had (free plan, offline, provider down), and
 * the Listen sheet then reads with the phone's own voice exactly as before.
 *
 * Audio is kept twice on the device: an object URL per text for this run of
 * the app, and the Cache Storage API so a brief played once still plays
 * offline. Cache Storage isn't guaranteed in every WebView, so both are
 * best-effort and keyed by the text itself, which is all the audio depends on.
 */
@Injectable({ providedIn: 'root' })
export class NaturalVoiceService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly connectivity = inject(ConnectivityService);
  private readonly entitlements = inject(EntitlementService);

  private entitled: { value: boolean; at: number } | null = null;
  private readonly urls = new Map<string, Promise<string>>();
  private readonly translations = new Map<string, Promise<{ label: string; text: string }[]>>();

  async available(): Promise<boolean> {
    if (this.entitled && Date.now() - this.entitled.at < ENTITLEMENT_TTL_MS) {
      return this.entitled.value;
    }
    try {
      const snapshot = await this.entitlements.snapshot();
      const value = snapshot.entitlements[ENTITLEMENT] === true;
      this.entitled = { value, at: Date.now() };
      return value;
    } catch {
      // Offline or signed out: still allow anything already cached on device.
      return this.entitled?.value ?? false;
    }
  }

  /**
   * Telugu text for a brief's sections, so Chirp's Telugu voice reads Telugu
   * words rather than English in a Telugu accent. Labels stay as given.
   */
  async telugu(sections: { label: string; text: string }[]): Promise<{ label: string; text: string }[]> {
    const key = JSON.stringify(sections);
    let pending = this.translations.get(key);
    if (!pending) {
      pending = this.loadTelugu(sections);
      this.translations.set(key, pending);
      pending.catch(() => this.translations.delete(key));
    }
    return pending;
  }

  private async loadTelugu(sections: { label: string; text: string }[]): Promise<{ label: string; text: string }[]> {
    if (this.connectivity.offline()) throw new Error('offline');
    const token = await this.auth.getAccessToken();
    const body = await firstValueFrom(
      this.http.post<{ sections: { label: string; text: string }[] }>(
        apiUrl('/api/v1/voice/translate'),
        { sections, language: 'te' },
        { headers: token ? { Authorization: `Bearer ${token}` } : {} },
      ),
    );
    if (!body?.sections?.length || body.sections.length !== sections.length) throw new Error('bad translation');
    return body.sections;
  }

  /** An object URL for `text` spoken naturally. Starts the request on first call. */
  audioUrl(text: string): Promise<string> {
    let pending = this.urls.get(text);
    if (!pending) {
      pending = this.load(text);
      this.urls.set(text, pending);
      // A failed request must not poison later attempts once back online.
      pending.catch(() => this.urls.delete(text));
    }
    return pending;
  }

  private async load(text: string): Promise<string> {
    const key = await cacheKey(text);
    const stored = await readCache(key);
    if (stored) return URL.createObjectURL(stored);
    if (this.connectivity.offline()) throw new Error('offline');

    const token = await this.auth.getAccessToken();
    const blob = await firstValueFrom(
      this.http.post(apiUrl('/api/v1/voice/speech'), { text, language: 'auto' }, {
        responseType: 'blob',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      }),
    );
    void writeCache(key, blob);
    return URL.createObjectURL(blob);
  }
}

/**
 * The first piece is kept short: the server makes each piece in full before
 * any of it plays, and a 1,000-character first piece took 12-16 s, so a short
 * opening sentence starts the voice in a second or two while the rest is made
 * during playback.
 */
export const NATURAL_FIRST_CHUNK_MAX_CHARS = 160;

/**
 * Splits text into request-sized pieces at sentence ends, never mid-sentence:
 * a short opening piece, then pieces of up to `max` characters.
 * Mirrored by natural_chunks in astrospace/notifications/daily_briefs.py, which
 * pre-renders the same pieces; the two must split identically.
 */
export function naturalChunks(text: string, max = NATURAL_CHUNK_MAX_CHARS): string[] {
  const clean = text.replace(/\s+/g, ' ').trim();
  if (!clean) return [];
  const opening = Math.min(NATURAL_FIRST_CHUNK_MAX_CHARS, max);
  if (clean.length <= opening) return [clean];
  const sentences = clean.split(/(?<=[.!?।])\s+/);
  const out: string[] = [];
  let first = sentences.shift() ?? '';
  while (sentences.length && first.length + 1 + sentences[0].length <= opening) {
    first = `${first} ${sentences.shift()}`;
  }
  out.push(first);
  let current = '';
  for (const sentence of sentences) {
    if (current && current.length + 1 + sentence.length > max) {
      out.push(current);
      current = '';
    }
    current = current ? `${current} ${sentence}` : sentence;
  }
  if (current) out.push(current);
  return out;
}

async function cacheKey(text: string): Promise<string> {
  try {
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
    const hex = Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, '0')).join('');
    return `https://natural-voice.local/${hex}.mp3`;
  } catch {
    return '';
  }
}

async function readCache(key: string): Promise<Blob | null> {
  if (!key || typeof caches === 'undefined') return null;
  try {
    const cache = await caches.open(CACHE_NAME);
    const hit = await cache.match(key);
    return hit ? await hit.blob() : null;
  } catch {
    return null;
  }
}

async function writeCache(key: string, blob: Blob): Promise<void> {
  if (!key || typeof caches === 'undefined') return;
  try {
    const cache = await caches.open(CACHE_NAME);
    await cache.put(key, new Response(blob, { headers: { 'Content-Type': 'audio/mpeg' } }));
    // Briefs change daily, so only recent audio is worth keeping on device.
    const keys = await cache.keys();
    for (const old of keys.slice(0, Math.max(0, keys.length - CACHE_MAX_ENTRIES))) {
      await cache.delete(old);
    }
  } catch {
    // Best-effort only.
  }
}
