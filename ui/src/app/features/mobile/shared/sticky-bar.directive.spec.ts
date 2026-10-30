import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { StickyBarDirective } from './sticky-bar.directive';

@Component({
  standalone: true,
  imports: [StickyBarDirective],
  template: `
    <main class="content" style="display: block; height: 300px; overflow-y: auto">
      <section>
        <!-- position: sticky comes from styles-mobile.scss in the app. -->
        <a class="bar" asStickyBar style="display: block; height: 50px; position: sticky; top: 0">Chart</a>
        <h1 style="height: 60px; margin: 0">Yogas and doshas</h1>
        <div style="height: 2000px"></div>
      </section>
    </main>
    <main class="content" style="display: block; height: 300px; overflow-y: auto">
      <header class="own" asStickyBar style="display: block; height: 50px"><h1>Calendar</h1></header>
      <div style="height: 2000px"></div>
    </main>
  `,
})
class HostComponent {}

const frame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));

describe('StickyBarDirective', () => {
  let root: HTMLElement;

  beforeEach(async () => {
    const fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
    root = fixture.nativeElement;
    document.body.appendChild(root);
    await frame();
  });

  afterEach(() => root.remove());

  async function scrollTo(scroller: HTMLElement, top: number): Promise<void> {
    scroller.scrollTop = top;
    scroller.dispatchEvent(new Event('scroll'));
    await frame();
  }

  it('marks the bar sticky and leaves it plain at the top of the page', () => {
    const bar = root.querySelector<HTMLElement>('a.bar')!;
    expect(bar.classList).toContain('m-sticky-bar');
    expect(bar.classList).not.toContain('is-scrolled');
    expect(bar.classList).not.toContain('is-collapsed');
    expect(bar.getAttribute('data-title')).toBe('Yogas and doshas');
  });

  it('frosts once the page moves, and shows the title small once the big one is under the bar', async () => {
    const [scroller] = Array.from(root.querySelectorAll<HTMLElement>('main.content'));
    const bar = root.querySelector<HTMLElement>('a.bar')!;

    await scrollTo(scroller, 20);
    expect(bar.classList).toContain('is-scrolled');
    expect(bar.classList).not.toContain('is-collapsed');

    await scrollTo(scroller, 200);
    expect(bar.classList).toContain('is-collapsed');

    await scrollTo(scroller, 0);
    expect(bar.classList).not.toContain('is-scrolled');
    expect(bar.classList).not.toContain('is-collapsed');
  });

  it('never adds a second title to a bar that carries its own', async () => {
    const scroller = root.querySelectorAll<HTMLElement>('main.content')[1];
    const bar = root.querySelector<HTMLElement>('header.own')!;
    await scrollTo(scroller, 400);
    expect(bar.classList).toContain('is-scrolled');
    expect(bar.classList).not.toContain('is-collapsed');
    expect(bar.hasAttribute('data-title')).toBeFalse();
  });
});
