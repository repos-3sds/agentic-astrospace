import { Component, OnDestroy, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterOutlet } from '@angular/router';
import { map } from 'rxjs';

import { KundliStore } from '../../../core/kundli.store';

@Component({
  selector: 'app-kundli-page',
  imports: [RouterOutlet],
  templateUrl: './kundli-page.component.html',
  styleUrl: './kundli-page.component.scss',
})
export class KundliPageComponent implements OnDestroy {
  protected readonly store = inject(KundliStore);
  private route = inject(ActivatedRoute);

  private routeId = toSignal(this.route.paramMap.pipe(map((p) => p.get('id'))));

  constructor() {
    // keep the store's active kundli in sync with the URL
    const sync = () => this.store.activeId.set(this.routeId() ?? null);
    this.route.paramMap.subscribe(() => sync());
  }

  ngOnDestroy(): void {
    this.store.activeId.set(null);
  }
}
