"""Turn a mantra keyed in a print's own spelling into the corpus spelling.

The Subhashita rules apply unchanged (scripts/subhashita/rekey/normalise.py).
Two more cover Weber's Madhyandina Vajasaneyi print; like the others they
change spelling, never a reading. Listed in docs/mantra_corpus.md.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "subhashita", "rekey"))
from normalise import normalise as _subhashita  # noqa: E402

# The print leaves out an avagraha that sandhi calls for (तमोरिं, Navagraha Stotra v.1).
AVAGRAHA = {'तमोरिं': 'तमोऽरिं'}


def madhyandina(s):
    # ꣳ is the Madhyandina anusvara before a sibilant; it is said as an ordinary anusvara
    s = s.replace('ꣳ', 'ं')
    # the Madhyandina print marks a hiatus before an independent vowel with avagraha (येऽअन्तरिक्षे)
    return re.sub(r'ऽ(?=[अआइईउऊऋएऐओऔ])', ' ', s)


def normalise(s):
    s = _subhashita(madhyandina(s))
    for printed, restored in AVAGRAHA.items():
        s = s.replace(printed, restored)
    return s
