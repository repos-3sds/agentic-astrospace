import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Title } from '@angular/platform-browser';
import { Router, TitleStrategy, provideRouter } from '@angular/router';
import { SiddhaTitleStrategy } from './siddha-title.strategy';

@Component({ template: '' })
class BlankComponent {}

describe('SiddhaTitleStrategy', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: 'calendar', title: 'Calendar', component: BlankComponent },
          { path: 'untitled', component: BlankComponent },
        ]),
        { provide: TitleStrategy, useClass: SiddhaTitleStrategy },
      ],
    });
  });

  it('names the screen, which screen readers announce on navigation', async () => {
    await TestBed.inject(Router).navigateByUrl('/calendar');
    expect(TestBed.inject(Title).getTitle()).toBe('Calendar · Siddha');
  });

  it('keeps the app title on screens without one', async () => {
    await TestBed.inject(Router).navigateByUrl('/untitled');
    expect(TestBed.inject(Title).getTitle()).toBe('Siddha — Your Guide to Living in Rhythm');
  });
});
