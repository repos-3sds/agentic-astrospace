import { normalizeProfileRelationship } from './profile-fields';

describe('normalizeProfileRelationship', () => {
  it('maps legacy family labels to canonical dropdown values', () => {
    expect(normalizeProfileRelationship('wife')).toBe('spouse');
    expect(normalizeProfileRelationship('Mother')).toBe('parent');
    expect(normalizeProfileRelationship('daughter')).toBe('child');
  });

  it('keeps supported values and safely contains unknown legacy labels', () => {
    expect(normalizeProfileRelationship('friend')).toBe('friend');
    expect(normalizeProfileRelationship('cousin')).toBe('relative');
  });
});
