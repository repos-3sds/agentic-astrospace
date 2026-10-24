import { Capacitor } from '@capacitor/core';
import { applySavedTextSize, TextSizeService } from './text-size.service';

describe('TextSizeService on iPhone', () => {
  const adjust = () => (document.body.style as CSSStyleDeclaration & { webkitTextSizeAdjust?: string }).webkitTextSizeAdjust;

  beforeEach(() => {
    spyOn(Capacitor, 'getPlatform').and.returnValue('ios');
    localStorage.removeItem('siddha_text_size');
  });

  afterEach(() => {
    localStorage.removeItem('siddha_text_size');
    (document.body.style as CSSStyleDeclaration & { webkitTextSizeAdjust?: string }).webkitTextSizeAdjust = '';
  });

  it('shows the row and scales the text, then restores it on the next launch', async () => {
    const service = new TextSizeService();
    expect(service.available).toBeTrue();
    expect(service.readsPhone).toBeFalse();

    await service.set(130);
    expect(adjust()).toBe('130%');
    expect(localStorage.getItem('siddha_text_size')).toBe('130');

    (document.body.style as CSSStyleDeclaration & { webkitTextSizeAdjust?: string }).webkitTextSizeAdjust = '';
    applySavedTextSize();
    expect(adjust()).toBe('130%');

    await new TextSizeService().load();
  });

  it('treats a missing or unknown saved value as the design size', async () => {
    localStorage.setItem('siddha_text_size', '777');
    const service = new TextSizeService();
    await service.load();
    expect(service.choice()).toBe(0);
    applySavedTextSize();
    expect(adjust()).toBe('100%');
  });
});
