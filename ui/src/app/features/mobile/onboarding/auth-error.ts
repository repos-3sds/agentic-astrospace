/** Loose shape check, only to catch typos before a round trip; the auth
 * server stays the judge of what is a real address. */
export function looksLikeEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

/**
 * Supabase's auth errors are written for developers ("Unable to validate
 * email address: invalid format"). Map the ones a reader can hit to plain
 * words; anything unrecognised gets a generic line rather than the raw text.
 */
export function authErrorMessage(error: unknown, fallback = 'That didn’t work. Try again in a moment.'): string {
  const raw = (error as { message?: string } | null)?.message ?? '';
  const text = raw.toLowerCase();
  if (text.includes('invalid format') || text.includes('validate email')) return 'That email address doesn’t look right. Check it and try again.';
  if (text.includes('invalid login credentials')) return 'That email and password don’t match. Try again, or reset your password.';
  if (text.includes('email not confirmed')) return 'Confirm your email first. Check your inbox for the link we sent.';
  if (text.includes('already registered') || text.includes('already been registered')) return 'An account already uses this email. Sign in instead.';
  if (text.includes('rate limit') || text.includes('too many') || text.includes('security purposes')) return 'Too many tries just now. Wait a minute, then try again.';
  if (text.includes('password should') || text.includes('weak password')) return 'Choose a stronger password: longer, with a mix of letters and numbers.';
  if (text.includes('failed to fetch') || text.includes('network')) return 'No connection. Check your internet and try again.';
  if (raw) console.warn('auth error', raw);
  return fallback;
}
