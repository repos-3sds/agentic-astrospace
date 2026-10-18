import { aboutSomeoneElse } from './ask-home.component';

describe('aboutSomeoneElse', () => {
  it('names the person whose chart is open', () => {
    expect(aboutSomeoneElse('What does my Moon period mean for work right now?', 'Ravi'))
      .toBe('What does Ravi’s Moon period mean for work right now?');
    expect(aboutSomeoneElse('My career: what helps me this month?', 'Ravi'))
      .toBe('Ravi’s career: what helps Ravi this month?');
    expect(aboutSomeoneElse('Is mystery myth?', 'Ravi')).toBe('Is mystery myth?');
  });
});
