import { pageMotion } from './page-transitions';

describe('pageMotion', () => {
  it('crossfades between tab roots', () => {
    expect(pageMotion('/m/today', '/m/explore', 'imperative')).toBe('tab');
    expect(pageMotion('/m/ask?x=1', '/m/calendar', 'popstate')).toBe('tab');
  });

  it('pushes deeper and pops on Back', () => {
    expect(pageMotion('/m/explore', '/m/chart', 'imperative')).toBe('push');
    expect(pageMotion('/m/chart', '/m/explore', 'popstate')).toBe('pop');
  });

  it('leaves the web app and same-page changes alone', () => {
    expect(pageMotion('/dashboard', '/today', 'imperative')).toBeNull();
    expect(pageMotion('/m/today', '/m/today?tab=2', 'imperative')).toBeNull();
    expect(pageMotion('/m/today', '/login', 'imperative')).toBeNull();
  });
});
