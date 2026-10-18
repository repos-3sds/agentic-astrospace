import { DestroyRef, Signal, effect } from '@angular/core';

interface WakeLockSentinelLike {
  released: boolean;
  release(): Promise<void>;
}

interface WakeLockLike {
  request(type: 'screen'): Promise<WakeLockSentinelLike>;
}

/**
 * Keeps the screen on while `active()` is true, through the Screen Wake Lock
 * API the Android WebView (and iOS 18.4+ WKWebView) supports. A locked screen
 * suspends the WebView, which is what stops Listen and mantra Auto mid-way.
 * The OS drops the lock whenever the app is hidden, so it is taken again on
 * return. Where the API is missing this does nothing: the screen times out as
 * before. Lock-screen controls and background audio need a native plugin; see
 * the deferred backlog (N5).
 */
export function keepScreenAwakeWhile(active: Signal<boolean>, destroyRef: DestroyRef): void {
  const wakeLock = typeof navigator !== 'undefined'
    ? (navigator as Navigator & { wakeLock?: WakeLockLike }).wakeLock
    : undefined;
  if (!wakeLock || typeof document === 'undefined') return;

  let sentinel: WakeLockSentinelLike | null = null;
  let wanted = false;

  const acquire = () => {
    if (!wanted || document.visibilityState !== 'visible') return;
    if (sentinel && !sentinel.released) return;
    wakeLock.request('screen').then(
      lock => {
        if (wanted) sentinel = lock;
        else void lock.release().catch(() => undefined);
      },
      () => undefined,
    );
  };
  const release = () => {
    const held = sentinel;
    sentinel = null;
    if (held && !held.released) void held.release().catch(() => undefined);
  };
  const onVisible = () => acquire();

  document.addEventListener('visibilitychange', onVisible);
  effect(() => {
    wanted = active();
    if (wanted) acquire();
    else release();
  });
  destroyRef.onDestroy(() => {
    wanted = false;
    document.removeEventListener('visibilitychange', onVisible);
    release();
  });
}
