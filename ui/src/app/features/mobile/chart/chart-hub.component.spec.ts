import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';

import { KundliStore } from '../../../core/kundli.store';
import { PreferencesService } from '../../../core/preferences.service';
import { VedicService } from '../../../core/vedic.service';
import { ChartHubComponent } from './chart-hub.component';

describe('ChartHubComponent practitioner gateways', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: KundliStore,
          useValue: {
            activeId: signal<string | null>(null),
            active: signal(null),
            load: () => Promise.resolve(),
          },
        },
        {
          provide: VedicService,
          useValue: {
            cachedAll: () => null,
          },
        },
        {
          provide: PreferencesService,
          useValue: {
            experienceMode: signal('practitioner'),
            chartStyle: signal('south'),
            nodeType: signal('mean'),
          },
        },
      ],
    });
  });

  it('keeps Ask featured and exposes Birth Details before the chart tools', () => {
    const component = TestBed.runInInjectionContext(() => new ChartHubComponent());
    const tiles = (component as unknown as {
      yantraTiles: () => Array<{ title: string; route: string[]; featured?: boolean }>;
    }).yantraTiles();

    expect(tiles[0]).toEqual(jasmine.objectContaining({ title: 'Ask Siddha', featured: true }));
    expect(tiles[1]).toEqual(jasmine.objectContaining({
      title: 'Birth Details',
      route: ['/m', 'chart', 'birth-details'],
    }));
    expect(tiles[2].title).toBe('Charts & Vargas');
  });

  it('builds the Dasha clock rows with how far through each period is', () => {
    const component = TestBed.runInInjectionContext(() => new ChartHubComponent());
    const year = 365.25 * 24 * 3600 * 1000;
    const now = Date.now();
    const iso = (offset: number) => new Date(now + offset).toISOString();
    const hub = component as unknown as {
      dashas: { set: (value: unknown) => void };
      dashaRows: () => Array<{ level: string; lord: string; pct: number }>;
      glyph: (lord: string) => string;
    };
    hub.dashas.set({
      current: {
        mahadasha: { lord: 'Jupiter', start: iso(-4 * year), end: iso(12 * year), years: 16, active: true },
        antardasha: { lord: 'Rahu', start: iso(-1 * year), end: iso(1 * year), years: 2, active: true },
        pratyantardashas: [],
      },
    });

    const rows = hub.dashaRows();
    expect(rows.map((row) => row.level)).toEqual(['Mahādasha', 'Antardasha']);
    expect(rows[0].pct).toBe(25);
    expect(rows[1].pct).toBe(50);
    expect(hub.glyph('Jupiter')).toBe('♃');
  });
});
