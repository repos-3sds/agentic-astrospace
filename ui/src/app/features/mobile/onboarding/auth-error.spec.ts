import { authErrorMessage, isEmailNotConfirmed, looksLikeEmail } from './auth-error';

describe('auth errors', () => {
  it('turns Supabase’s developer wording into plain words', () => {
    expect(authErrorMessage(new Error('Unable to validate email address: invalid format')))
      .toBe('That email address doesn’t look right. Check it and try again.');
    expect(authErrorMessage(new Error('Invalid login credentials'))).toContain('don’t match');
  });

  it('never shows an unknown raw error', () => {
    spyOn(console, 'warn');
    expect(authErrorMessage(new Error('AuthApiError: unexpected_failure 500'), 'Try again.')).toBe('Try again.');
  });

  it('catches an obvious typo before sending', () => {
    expect(looksLikeEmail('notanemail')).toBeFalse();
    expect(looksLikeEmail(' reader@example.com ')).toBeTrue();
  });

  it('spots an unconfirmed account by code or by message', () => {
    expect(isEmailNotConfirmed({ code: 'email_not_confirmed', message: '' })).toBeTrue();
    expect(isEmailNotConfirmed(new Error('Email not confirmed'))).toBeTrue();
    expect(isEmailNotConfirmed(new Error('Invalid login credentials'))).toBeFalse();
    expect(isEmailNotConfirmed(null)).toBeFalse();
  });
});
