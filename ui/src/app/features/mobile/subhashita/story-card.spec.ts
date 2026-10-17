import { longDate, renderStoryCard, shareText, STORY_HEIGHT, STORY_WIDTH } from './story-card';

describe('story card', () => {
  const verse = {
    date: '2026-10-17', id: 'gita-2-47', source: 'Bhagavad Gita', ref: '2.47',
    sanskrit: 'कर्मण्येवाधिकारस्ते मा फलेषु कदाचन।\nमा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि॥',
    english: 'Your part is the work itself, never its fruits. Do not work for the reward, and do not walk away from the work.',
  };

  it('is a 9:16 status image', async () => {
    const canvas = await renderStoryCard(verse);
    expect([canvas.width, canvas.height]).toEqual([STORY_WIDTH, STORY_HEIGHT]);
    expect(STORY_HEIGHT / STORY_WIDTH).toBeCloseTo(16 / 9, 2);
  });

  it('names the day from its parts, so no timezone moves it', () => {
    expect(longDate('2026-10-17')).toBe('Saturday, 17 October');
  });

  it('shares the words with their source and where they came from', () => {
    const text = shareText(verse);
    expect(text).toContain(verse.sanskrit);
    expect(text).toContain('— Bhagavad Gita 2.47');
    expect(text).toContain('https://asksiddha.app');
  });
});
