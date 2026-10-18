import { SessionTeardown, USER_LOCAL_STORAGE_KEYS } from './session-teardown';

describe('SessionTeardown', () => {
  afterEach(() => {
    localStorage.removeItem('astrospace.theme.test');
    for (const key of USER_LOCAL_STORAGE_KEYS) localStorage.removeItem(key);
  });

  it('forgets the signed-out person’s notes but keeps device settings', () => {
    localStorage.setItem('astrospace.mobile.notes.draft', 'private draft');
    localStorage.setItem('astrospace.theme.test', 'dark');

    new SessionTeardown().run();

    expect(localStorage.getItem('astrospace.mobile.notes.draft')).toBeNull();
    expect(localStorage.getItem('astrospace.theme.test')).toBe('dark');
  });

  it('keeps running hooks when one throws', () => {
    const teardown = new SessionTeardown();
    const later = jasmine.createSpy('later');
    spyOn(console, 'error');
    teardown.register(() => {
      throw new Error('boom');
    });
    teardown.register(later);

    teardown.run();

    expect(later).toHaveBeenCalled();
  });
});
