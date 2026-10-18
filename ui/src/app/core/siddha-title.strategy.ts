import { Injectable, inject } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { RouterStateSnapshot, TitleStrategy } from '@angular/router';

export const APP_TITLE = 'Siddha';

/**
 * Names each screen in the document title ("Calendar · Siddha"), which is
 * what TalkBack and VoiceOver read when the screen changes. Routes without a
 * title keep the app's own.
 */
@Injectable({ providedIn: 'root' })
export class SiddhaTitleStrategy extends TitleStrategy {
  private readonly title = inject(Title);

  override updateTitle(snapshot: RouterStateSnapshot): void {
    const screen = this.buildTitle(snapshot);
    this.title.setTitle(screen ? `${screen} · ${APP_TITLE}` : `${APP_TITLE} — Your Guide to Living in Rhythm`);
  }
}
