import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { signal } from '@angular/core';
import { PanchangAlarmsComponent } from './panchang-alarms.component';
import { DEFAULT_ALARMS, PanchangAlarm, PanchangAlarmService } from '../../../core/panchang-alarm.service';
import { KundliStore } from '../../../core/kundli.store';
import { PanchangaService } from '../../../core/panchanga.service';
import { PreferencesService } from '../../../core/preferences.service';
import { PushService } from '../../../core/push.service';

class AlarmStub {
  alarms = signal<PanchangAlarm[]>(DEFAULT_ALARMS.map((a) => ({ ...a })));
  error = signal<string | null>(null);
  exact = signal<'granted' | 'denied' | 'unsupported'>('unsupported');
  native = false;
  update = (id: string, patch: Partial<PanchangAlarm>) =>
    this.alarms.update((all) => all.map((a) => (a.id === id ? { ...a, ...patch } : a)));
  refreshExact = async () => undefined;
  requestExact = async () => undefined;
  reschedule = async () => undefined;
}

describe('PanchangAlarmsComponent', () => {
  let fixture: ComponentFixture<PanchangAlarmsComponent>;
  let alarms: AlarmStub;

  beforeEach(async () => {
    alarms = new AlarmStub();
    await TestBed.configureTestingModule({
      imports: [PanchangAlarmsComponent],
      providers: [
        provideRouter([]),
        { provide: PanchangAlarmService, useValue: alarms },
        { provide: KundliStore, useValue: { loaded: () => true, owner: () => null, active: () => null, load: async () => undefined } },
        { provide: PanchangaService, useValue: { today: async () => null } },
        { provide: PreferencesService, useValue: { panchangaPlace: signal(null) } },
        { provide: PushService, useValue: { permission: signal('unsupported'), refreshPermission: async () => 'unsupported', enable: async () => 'unsupported' } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(PanchangAlarmsComponent);
    fixture.detectChanges();
  });

  const el = () => fixture.nativeElement as HTMLElement;
  const states = () =>
    Array.from(el().querySelectorAll('.alarm-head .switch')).map((s) => (s.getAttribute('aria-checked') === 'true' ? '1' : '0')).join('');
  const tops = () => Array.from(el().querySelectorAll('.alarm')).map((row) => row.querySelector('.editor') !== null);
  const tap = (label: string) => {
    (el().querySelector(`button[aria-label="${label} alarm"]`) as HTMLButtonElement).click();
    fixture.detectChanges();
  };

  it('a switch changes only itself and opens nothing (Deepak, 2026-10-28)', () => {
    expect(states()).toBe('001000100000');
    tap('Sunrise');
    expect(states()).toBe('011000100000');
    tap('Godhuli');
    expect(states()).toBe('011010100000');
    tap('Sunrise');
    expect(states()).toBe('001010100000');
    // No editor appeared, so no row moved under the reader's thumb.
    expect(tops().some(Boolean)).toBeFalse();
  });

  it('opens "when" and "how" from the row, and closes it when switched off', () => {
    const row = () => el().querySelectorAll('.alarm-text')[2] as HTMLButtonElement; // Abhijit, on
    row().click();
    fixture.detectChanges();
    expect(el().querySelectorAll('.editor').length).toBe(1);
    tap('Abhijit Muhurta');
    expect(el().querySelectorAll('.editor').length).toBe(0);
    expect(states()).toBe('000000100000');
  });

  it('keeps an open editor where it is when another switch is tapped', () => {
    (el().querySelectorAll('.alarm-text')[2] as HTMLButtonElement).click();
    fixture.detectChanges();
    tap('Yamaganda');
    expect(el().querySelectorAll('.editor').length).toBe(1);
    expect(states()).toBe('001000110000');
  });
});
