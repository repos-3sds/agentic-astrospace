import { Injectable, inject } from '@angular/core';

import { ApiService } from './api.service';
import { FestivalWindowPayload } from './models';

@Injectable({ providedIn: 'root' })
export class FestivalService {
  private readonly api = inject(ApiService);
  private readonly cache = new Map<string, Promise<FestivalWindowPayload>>();

  upcoming(
    city: string,
    nation: string,
    fromDate: string,
    days: number,
  ): Promise<FestivalWindowPayload> {
    const params = new URLSearchParams({
      city,
      nation,
      from_date: fromDate,
      days: String(days),
    });
    const key = params.toString();
    let cached = this.cache.get(key);
    if (!cached) {
      cached = this.api.get<FestivalWindowPayload>(`/festivals/upcoming?${key}`).catch((error) => {
        this.cache.delete(key);
        throw error;
      });
      this.cache.set(key, cached);
    }
    return cached;
  }
}
