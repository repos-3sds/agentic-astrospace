import { YogaResult, YogasDoshasPayload } from '../../../core/models';
import { buildCombinations } from './combinations';

function yoga(rule_id: string, name: string, strength: string, extra: Partial<YogaResult> = {}): YogaResult {
  return {
    rule_id, name, strength, category: 'Raja / Status', active: true, rule: 'rule', triggers: [], planets: [],
    verified: true, why: [`why ${name}`], reader: { what: `what ${name}`, do: ['d'], avoid: ['a'] }, ...extra,
  };
}

function payload(active: YogaResult[], all: YogaResult[] = active): YogasDoshasPayload {
  return {
    yogas: { active, all, locked_count: 0 } as YogasDoshasPayload['yogas'],
    doshas: {
      manglik: {
        name: 'Manglik', active: true, severity: 'mild', rule: 'r', why: ['Mars from Lagna'],
        exceptions: [{ applies: true, detail: 'own sign', plain: 'Mars is in its own sign.' }, { applies: false, detail: 'x', plain: 'no aspect' }],
      },
      gandanta: { name: 'Gandanta Dosha', active: false, severity: 'mild', rule: 'r' },
    } as unknown as YogasDoshasPayload['doshas'],
  };
}

describe('buildCombinations', () => {
  const caution = yoga('kemadruma_yoga', 'Kemadruma Yoga', 'moderate', { category: 'Caution / Effort' });
  const rows = [
    yoga('amala_yoga', 'Amala Yoga', 'weak'),
    yoga('gajakesari_yoga', 'Gajakesari Yoga', 'strong'),
    yoga('hamsa_yoga', 'Hamsa Yoga', 'moderate'),
    caution,
  ];

  it('shows every flag on Free and only two strengths, strongest first', () => {
    const view = buildCombinations(payload(rows), 'guided', false);
    expect(view.strengths.map((c) => c.title)).toEqual(['Gajakesari Yoga', 'Hamsa Yoga']);
    expect(view.hiddenYogas).toBe(1);
    expect(view.flags.map((c) => c.title)).toEqual(['Manglik (Kuja) Dosha', 'Kemadruma Yoga']);
  });

  it('says what softens a dosha and what was checked without effect', () => {
    const manglik = buildCombinations(payload(rows), 'balanced', true).flags[0];
    expect(manglik.kind).toBe('dosha');
    expect(manglik.tag).toContain('Softened');
    expect(manglik.softens).toEqual(['Mars is in its own sign.']);
    expect(manglik.alsoChecked).toEqual(['no aspect']);
  });

  it('keeps one-way Raja links for Practitioner and groups pairs into one card', () => {
    const raja = [
      yoga('raja_yoga', 'Raja Yoga: Venus-Saturn', 'moderate'),
      yoga('raja_yoga', 'Raja Yoga: Sun-Jupiter', 'weak', { partial: true }),
    ];
    expect(buildCombinations(payload(raja), 'balanced', true).strengths[0].why).toEqual(['why Raja Yoga: Venus-Saturn']);
    const pro = buildCombinations(payload(raja), 'practitioner', true).strengths;
    expect(pro.length).toBe(1);
    expect(pro[0].title).toBe('Raja Yoga');
    expect(pro[0].why.length).toBe(2);
  });

  it('lists cancelled yogas and absent doshas as checked', () => {
    const cancelled = { ...caution, active: false, cancelled: true, cancellations: ['Venus is in a kendra from Lagna.'] };
    const view = buildCombinations(payload(rows.slice(0, 3), [...rows.slice(0, 3), cancelled]), 'guided', true);
    expect(view.checked.map((r) => r.note)).toEqual(['checked and cancelled', 'not in your chart']);
    expect(view.checked[0].item?.softens).toEqual(['Venus is in a kendra from Lagna.']);
  });
});
