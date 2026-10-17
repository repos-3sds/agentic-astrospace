export const PROFILE_RELATIONSHIPS = [
  { value: 'self', label: 'Myself' },
  { value: 'spouse', label: 'Spouse' },
  { value: 'partner', label: 'Partner' },
  { value: 'child', label: 'Child' },
  { value: 'parent', label: 'Parent' },
  { value: 'grandparent', label: 'Grandparent' },
  { value: 'grandchild', label: 'Grandchild' },
  { value: 'sibling', label: 'Sibling' },
  { value: 'relative', label: 'Other family' },
  { value: 'friend', label: 'Friend' },
  { value: 'client', label: 'Client' },
  { value: 'prospect', label: 'Prospect' },
] as const;

export function normalizeProfileRelationship(value: string | null | undefined): string {
  const relation = (value || '').trim().toLowerCase();
  if (['wife', 'husband'].includes(relation)) return 'spouse';
  if (['mother', 'father'].includes(relation)) return 'parent';
  if (['son', 'daughter'].includes(relation)) return 'child';
  if (['brother', 'sister'].includes(relation)) return 'sibling';
  return PROFILE_RELATIONSHIPS.some((option) => option.value === relation) ? relation : 'relative';
}

/** What a profile is to the account holder, as a label. Stored values are
 * free text from older builds ("relative", "Mother"), so they are normalised
 * first rather than shown raw. */
export function profileRelationLabel(value: string | null | undefined): string {
  const relation = normalizeProfileRelationship(value);
  if (relation === 'self') return 'You';
  return PROFILE_RELATIONSHIPS.find((option) => option.value === relation)?.label ?? 'Profile';
}
