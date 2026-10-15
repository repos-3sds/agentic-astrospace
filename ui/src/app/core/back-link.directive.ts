import { Location } from '@angular/common';
import { Directive, HostBinding, HostListener, computed, inject, input } from '@angular/core';
import { Params, Router } from '@angular/router';

import { NavigationHistoryService } from './navigation-history.service';

/**
 * A back control that goes back.
 *
 * `asBack` names the fallback (route commands or a path string), used only
 * when there is no in-app screen behind this one — a deep link, a push
 * notification, a fresh launch. Otherwise the tap is a real `history.back()`,
 * so a screen reached from three places returns to each of them. The
 * fallback is also written to `href`, so the link reads as one to assistive
 * tech and to a long press.
 */
@Directive({
  selector: 'a[asBack]',
  standalone: true,
})
export class BackLinkDirective {
  private readonly router = inject(Router);
  private readonly location = inject(Location);
  private readonly history = inject(NavigationHistoryService);

  readonly asBack = input.required<string | readonly unknown[] | null>();
  readonly asBackQueryParams = input<Params | null>(null);

  private readonly commands = computed<unknown[]>(() => {
    const value = this.asBack();
    if (value === null) return ['/m', 'today'];
    return typeof value === 'string' ? [value] : [...value];
  });

  @HostBinding('attr.href')
  get href(): string {
    const tree = this.router.createUrlTree(this.commands() as string[], { queryParams: this.asBackQueryParams() ?? undefined });
    return this.router.serializeUrl(tree);
  }

  @HostListener('click', ['$event'])
  onClick(event: MouseEvent): boolean {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return true;
    event.preventDefault();
    if (this.history.canGoBack()) {
      this.location.back();
    } else {
      void this.router.navigate(this.commands() as string[], { queryParams: this.asBackQueryParams() ?? undefined });
    }
    return false;
  }
}
