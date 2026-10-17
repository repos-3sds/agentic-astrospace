import { normalizeProfileRelationship, profileRelationLabel } from './profile-fields';

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

describe('profileRelationLabel', () => {
  it('labels the account holder as You and never shows a raw stored value', () => {
    expect(profileRelationLabel('Self')).toBe('You');
    expect(profileRelationLabel('mother')).toBe('Parent');
    expect(profileRelationLabel(null)).toBe('Other family');
  });
});
