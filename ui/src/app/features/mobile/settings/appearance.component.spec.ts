import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { AppearanceComponent } from './appearance.component';
import { WidgetBridgeService } from '../../../core/widget-bridge.service';

class WidgetsStub {
  constructor(private readonly stored: number | null) {}
  saved: number[] = [];
  opacity = async () => this.stored;
  setOpacity = async (percent: number) => {
    this.saved.push(percent);
  };
}

async function render(stored: number | null) {
  const widgets = new WidgetsStub(stored);
  TestBed.configureTestingModule({
    imports: [AppearanceComponent],
    providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting(), { provide: WidgetBridgeService, useValue: widgets }],
  });
  const fixture = TestBed.createComponent(AppearanceComponent);
  fixture.detectChanges();
  await fixture.whenStable();
  fixture.detectChanges();
  return { fixture, widgets, el: fixture.nativeElement as HTMLElement };
}

describe('AppearanceComponent widget opacity', () => {
  it('hides the widget setting off Android', async () => {
    const { el } = await render(null);
    expect(el.querySelector('#widget-opacity')).toBeNull();
    expect(el.textContent).not.toContain('HOME SCREEN WIDGETS');
  });

  it('shows the stored value and saves only on release', async () => {
    const { el, widgets, fixture } = await render(70);
    const slider = el.querySelector<HTMLInputElement>('#widget-opacity')!;
    expect(slider.value).toBe('70');
    expect(el.querySelector('.opacity-value')!.textContent).toContain('70%');

    slider.value = '40';
    slider.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    expect(el.querySelector('.opacity-value')!.textContent).toContain('40%');
    expect(widgets.saved).toEqual([]);

    slider.dispatchEvent(new Event('change'));
    expect(widgets.saved).toEqual([40]);
  });
});
