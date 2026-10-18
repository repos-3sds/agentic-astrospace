import { Injectable } from '@angular/core';

/**
 * One place that knows everything a sign-out has to forget.
 *
 * Per-user state lives in services that AuthService cannot inject without a
 * cycle (the route-reuse strategy is built by the Router, which AuthService
 * itself depends on; KundliStore depends on ApiService, which depends on
 * AuthService). Each owner registers a hook here instead, and
 * AuthService.signOut() runs them all before it navigates away — so the next
 * account to sign in on the same phone starts from nothing.
 *
 * Dependency-free on purpose: anything may inject it.
 */
@Injectable({ providedIn: 'root' })
export class SessionTeardown {
  private readonly hooks = new Set<() => void>();

  /** Returns an unregister function. */
  register(hook: () => void): () => void {
    this.hooks.add(hook);
    return () => this.hooks.delete(hook);
  }

  run(): void {
    for (const hook of [...this.hooks]) {
      try {
        hook();
      } catch (error) {
        // One owner failing to clear must not stop the others.
        console.error('Sign-out teardown hook failed', error);
      }
    }
    clearUserSessionStorage();
    clearUserLocalStorage();
  }
}

/**
 * Per-tab copies of the signed-out account's data: the selected web profile
 * and recent Ask answers/threads. Those are written by components that may
 * never have been constructed this session, so they are swept by key prefix
 * rather than by a registered hook.
 */
function clearUserSessionStorage(): void {
  try {
    for (const key of Object.keys(sessionStorage)) {
      if (key.startsWith('astrospace')) sessionStorage.removeItem(key);
    }
  } catch {
    // Storage can be unavailable (private mode); nothing to clear then.
  }
}

/**
 * Device-wide (localStorage) values that belong to the signed-in person, not
 * to the phone. Theme, language and onboarding flags stay; these go. Notes
 * were left behind until 2026-10-18, so the next account to sign in on a
 * shared phone could read the previous person's private draft.
 */
export const USER_LOCAL_STORAGE_KEYS = ['astrospace.mobile.notes.draft'] as const;

function clearUserLocalStorage(): void {
  try {
    for (const key of USER_LOCAL_STORAGE_KEYS) localStorage.removeItem(key);
  } catch {
    // Storage can be unavailable (private mode); nothing to clear then.
  }
}
