import { Injectable, inject } from '@angular/core';

import { ApiService } from './api.service';
import { PredictionClaim, PredictionClaimStatus, Reading } from './models';

export type ReadingPeriod = 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly';

export const READING_PERIODS: ReadingPeriod[] = [
  'daily',
  'weekly',
  'monthly',
  'quarterly',
  'yearly',
];

@Injectable({ providedIn: 'root' })
export class ReadingService {
  private api = inject(ApiService);

  generate(kundliId: string, period: ReadingPeriod, forceRefresh = false): Promise<Reading> {
    return this.api.post<Reading>(`/readings/${kundliId}/generate`, {
      period,
      force_refresh: forceRefresh,
    });
  }

  list(kundliId: string, period?: ReadingPeriod): Promise<Reading[]> {
    const query = period ? `?period=${period}` : '';
    return this.api.get<Reading[]>(`/readings/${kundliId}${query}`);
  }

  feedback(
    kundliId: string,
    readingId: string,
    rating: number | null,
    feedback: string,
  ): Promise<Reading> {
    return this.api.patch<Reading>(`/readings/${kundliId}/${readingId}/feedback`, {
      rating,
      feedback,
    });
  }

  claims(kundliId: string, options: { status?: PredictionClaimStatus; startDate?: string; endDate?: string } = {}): Promise<PredictionClaim[]> {
    const params = new URLSearchParams();
    if (options.status) params.set('status', options.status);
    if (options.startDate) params.set('start_date', options.startDate);
    if (options.endDate) params.set('end_date', options.endDate);
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.api.get<PredictionClaim[]>(`/readings/${kundliId}/claims${query}`);
  }

  claimFeedback(
    kundliId: string,
    claimId: string,
    status: PredictionClaimStatus,
    feedback: string,
  ): Promise<PredictionClaim> {
    return this.api.patch<PredictionClaim>(`/readings/${kundliId}/claims/${claimId}`, {
      status,
      feedback,
    });
  }
}
