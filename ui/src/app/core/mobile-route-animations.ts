import {
  trigger,
  transition,
  style,
  query,
  group,
  animate,
} from '@angular/animations';

export const routeTransitionAnimations = trigger('routeTransition', [
  transition('* => *', [
    query(':enter, :leave', [
      style({
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
      })
    ], { optional: true }),
    query(':enter', [
      style({ opacity: 0 })
    ], { optional: true }),
    group([
      query(':leave', [
        animate('150ms ease-in', style({ opacity: 0 }))
      ], { optional: true }),
      query(':enter', [
        animate('250ms 50ms ease-out', style({ opacity: 1 }))
      ], { optional: true })
    ])
  ])
]);
