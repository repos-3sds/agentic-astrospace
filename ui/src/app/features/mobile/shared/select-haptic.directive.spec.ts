import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { HapticsService } from '../../../core/haptics.service';
import { SelectHapticDirective } from './select-haptic.directive';

@Component({
  standalone: true,
  imports: [SelectHapticDirective],
  template: `
    <div role="tablist" asSelectHaptic>
      @for (id of ids; track id) {
        <button type="button" role="tab" [id]="id" [attr.aria-selected]="current() === id" (click)="current.set(id)">{{ id }}</button>
      }
      <button type="button" id="off" disabled>off</button>
    </div>
  `,
})
class HostComponent {
  readonly ids = ['a', 'b'];
  readonly current = signal('a');
}

describe('SelectHapticDirective', () => {
  let select: jasmine.Spy;

  beforeEach(() => {
    select = jasmine.createSpy('select');
    TestBed.configureTestingModule({
      imports: [HostComponent],
      providers: [{ provide: HapticsService, useValue: { select } }],
    });
  });

  function setup() {
    const fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
    const click = (id: string) => {
      (fixture.nativeElement.querySelector(`#${id}`) as HTMLButtonElement).click();
      fixture.detectChanges();
    };
    return { click };
  }

  it('buzzes when the tap changes the choice', () => {
    const { click } = setup();
    click('b');
    expect(select).toHaveBeenCalledTimes(1);
  });

  it('stays quiet on the choice already selected', () => {
    const { click } = setup();
    click('a');
    expect(select).not.toHaveBeenCalled();
  });

  it('stays quiet on a disabled choice', () => {
    const { click } = setup();
    click('off');
    expect(select).not.toHaveBeenCalled();
  });
});
