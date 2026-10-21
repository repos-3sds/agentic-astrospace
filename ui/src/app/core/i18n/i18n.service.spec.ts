import { TestBed } from '@angular/core/testing';
import { EN } from './en';
import { I18nService } from './i18n.service';
import { TE } from './te';

describe('I18nService', () => {
  it('answers in English and refuses a UI language that is not ready', () => {
    const i18n = TestBed.inject(I18nService);
    expect(i18n.t('tab.today')).toBe('Today');
    expect(i18n.use('te')).toBeFalse();
    expect(i18n.current()).toBe('en');
  });

  it('keeps every Telugu key one that English has', () => {
    for (const key of Object.keys(TE)) expect(key in EN).withContext(key).toBeTrue();
  });
});
