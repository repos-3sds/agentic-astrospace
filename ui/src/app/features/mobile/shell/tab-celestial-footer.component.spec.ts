import { ComponentFixture, TestBed } from '@angular/core/testing';
import {
  TabCelestialFooterComponent,
  tabPlanetForPath,
} from './tab-celestial-footer.component';

describe('TabCelestialFooterComponent', () => {
  let fixture: ComponentFixture<TabCelestialFooterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TabCelestialFooterComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(TabCelestialFooterComponent);
  });

  it('renders the Moon asteroid belt only for Today', () => {
    fixture.componentRef.setInput('planet', 'moon');
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelectorAll('.asteroid-belt span').length).toBe(12);
    expect(fixture.nativeElement.querySelector('.saturn-ring')).toBeNull();
  });

  it('keeps celestial endings on exact primary routes', () => {
    expect(tabPlanetForPath('/m/today')).toBe('moon');
    expect(tabPlanetForPath('/m/ask')).toBe('mercury');
    expect(tabPlanetForPath('/m/explore')).toBe('earth');
    expect(tabPlanetForPath('/m/chart')).toBe('earth');
    expect(tabPlanetForPath('/m/chart/periods')).toBe('saturn');
    expect(tabPlanetForPath('/m/calendar')).toBe('jupiter');
    expect(tabPlanetForPath('/m/settings')).toBe('venus');
    expect(tabPlanetForPath('/m/chart/full')).toBeNull();
    expect(tabPlanetForPath('/m/calendar/2026-08-13')).toBeNull();
    expect(tabPlanetForPath('/m/settings/location')).toBeNull();
  });
});
