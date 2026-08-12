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
});
