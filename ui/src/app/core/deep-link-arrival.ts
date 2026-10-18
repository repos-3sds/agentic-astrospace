import { signal } from '@angular/core';

/**
 * When a push or widget tap last sent the reader somewhere (epoch ms). The
 * daily verse sheet reads it so it never covers the screen they tapped
 * through to (D8).
 */
export const deepLinkArrivedAt = signal(0);

export function noteDeepLink(): void {
  deepLinkArrivedAt.set(Date.now());
}
