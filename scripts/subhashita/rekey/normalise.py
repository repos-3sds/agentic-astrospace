"""Turn a verse keyed in a print's own spelling into the corpus spelling.

Every rule here is orthographic, never a change of reading: the words stay
the print's words. The rules are listed in docs/subhashita_corpus.md.
"""
import re

VIRAMA = '्'
MATRA = {'अ': '', 'आ': 'ा', 'इ': 'ि', 'ई': 'ी', 'उ': 'ु', 'ऊ': 'ू', 'ऋ': 'ृ', 'ॠ': 'ॄ',
         'ए': 'े', 'ऐ': 'ै', 'ओ': 'ो', 'औ': 'ौ'}
CLASS_NASAL = [('कखगघङ', 'ङ'), ('चछजझञ', 'ञ'), ('टठडढण', 'ण'), ('तथदधन', 'न'), ('पफबभम', 'म')]

# Prints of the period often leave out an avagraha that sandhi calls for
# (एकोपि for एकोऽपि). It is restored only where listed, word by word.
AVAGRAHA = {'प्रलयेपि': 'प्रलयेऽपि', 'एकोपि': 'एकोऽपि', 'कोप्रियः': 'कोऽप्रियः'}


def join(s):
    # split sandhi (Thomson 1855): a final consonant written apart from the next word
    s = re.sub(VIRAMA + r' ([अआइईउऊऋॠएऐओऔ])', lambda m: MATRA[m.group(1)], s)
    s = re.sub(VIRAMA + r' (?=[क-ह])', VIRAMA, s)
    s = s.replace(' ऽ', 'ऽ')
    # a final anusvara before a danda is a final म्
    return re.sub(r'ं(\s*[।॥])', r'म्\1', s)


def nasal(s):
    # anusvara before a stop is written as that stop's own nasal
    def f(m):
        for group, n in CLASS_NASAL:
            if m.group(1) in group:
                return n + VIRAMA + m.group(1)
        return m.group(0)
    return re.sub(r'ं([क-ह])', f, s)


def degeminate(s):
    # a consonant doubled after repha (र्त्त, र्व्व, र्द्ध) is written single
    s = re.sub(r'र्([क-ह])्\1', r'र्\1', s)
    return s.replace('र्द्ध', 'र्ध')


def elision(s):
    # an elided a after a long a, marked with avagraha (बुद्ध्याऽऽत्मना)
    return s.replace('ाऽऽ', 'ा').replace('ाऽ', 'ा')


def avagraha(s):
    for printed, restored in AVAGRAHA.items():
        s = s.replace(printed, restored)
    return s


def normalise(s):
    return avagraha(elision(degeminate(nasal(join(s)))))
