import { Location } from '@angular/common';
import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import { BackLinkDirective } from './back-link.directive';
import { NavigationHistoryService } from './navigation-history.service';

@Component({ standalone: true, template: '' })
class BlankComponent {}

@Component({
  standalone: true,
  imports: [BackLinkDirective],
  template: `<a [asBack]="['/settings']" aria-label="Back">back</a>`,
})
class HostComponent {}

describe('BackLinkDirective', () => {
  let router: Router;
  let location: Location;
  let history: NavigationHistoryService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostComponent],
      providers: [provideRouter([
        { path: 'settings', component: BlankComponent },
        { path: 'today', component: BlankComponent },
        { path: 'notifications', component: BlankComponent },
      ])],
    }).compileComponents();
    router = TestBed.inject(Router);
    location = TestBed.inject(Location);
    history = TestBed.inject(NavigationHistoryService);
  });

  function link(): HTMLAnchorElement {
    const fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
    return fixture.nativeElement.querySelector('a') as HTMLAnchorElement;
  }

  it('writes the fallback to href', () => {
    expect(link().getAttribute('href')).toBe('/settings');
  });

  it('falls back to the given route when the app has no screen behind this one', async () => {
    await router.navigateByUrl('/notifications');
    expect(history.canGoBack()).toBeFalse();
    const back = spyOn(location, 'back');
    link().click();
    for (let i = 0; i < 20 && router.url !== '/settings'; i += 1) await new Promise((r) => setTimeout(r, 10));
    expect(back).not.toHaveBeenCalled();
    expect(router.url).toBe('/settings');
  });

  it('does not count a URL replacement as a screen to go back to', async () => {
    await router.navigateByUrl('/today');
    await router.navigate(['/notifications'], { replaceUrl: true });
    expect(history.canGoBack()).toBeFalse();
  });

  it('goes back through in-app history when there is one', async () => {
    await router.navigateByUrl('/today');
    await router.navigateByUrl('/notifications');
    expect(history.canGoBack()).toBeTrue();
    const back = spyOn(location, 'back');
    link().click();
    expect(back).toHaveBeenCalled();
  });
});
