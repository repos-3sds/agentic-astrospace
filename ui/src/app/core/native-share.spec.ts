import { shareFile } from './native-share';

describe('shareFile', () => {
  const file = new File(['%PDF-1.4'], 'siddha.pdf', { type: 'application/pdf' });
  let originalShare: PropertyDescriptor | undefined;
  let originalCanShare: PropertyDescriptor | undefined;

  beforeEach(() => {
    originalShare = Object.getOwnPropertyDescriptor(navigator, 'share');
    originalCanShare = Object.getOwnPropertyDescriptor(navigator, 'canShare');
  });

  afterEach(() => {
    restore('share', originalShare);
    restore('canShare', originalCanShare);
  });

  it('returns false when the browser cannot share files, so callers download instead', async () => {
    Object.defineProperty(navigator, 'canShare', { configurable: true, value: () => false });
    Object.defineProperty(navigator, 'share', { configurable: true, value: async () => {} });
    expect(await shareFile(file, { title: 'Reading' })).toBeFalse();
  });

  it('hands the file to the Web Share API when the browser accepts files', async () => {
    const calls: ShareData[] = [];
    Object.defineProperty(navigator, 'canShare', { configurable: true, value: () => true });
    Object.defineProperty(navigator, 'share', { configurable: true, value: async (data: ShareData) => { calls.push(data); } });
    expect(await shareFile(file, { title: 'Reading', text: 'Q' })).toBeTrue();
    expect(calls[0].files?.[0]).toBe(file);
    expect(calls[0].title).toBe('Reading');
  });

  it('treats a dismissed share sheet as handled rather than as a failure', async () => {
    Object.defineProperty(navigator, 'canShare', { configurable: true, value: () => true });
    Object.defineProperty(navigator, 'share', {
      configurable: true,
      value: async () => { throw new DOMException('dismissed', 'AbortError'); },
    });
    expect(await shareFile(file, { title: 'Reading' })).toBeTrue();
  });

  function restore(key: 'share' | 'canShare', descriptor: PropertyDescriptor | undefined): void {
    if (descriptor) Object.defineProperty(navigator, key, descriptor);
    else delete (navigator as unknown as Record<string, unknown>)[key];
  }
});
