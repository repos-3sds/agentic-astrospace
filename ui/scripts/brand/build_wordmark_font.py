"""Build Siddha Mark, the wordmark face, from Rozha One (SIL OFL 1.1).

Rozha One's printable ASCII, with a headline bar (like the Devanagari
shirorekha) added to every letter so a word reads as one joined mark.
Renamed as the OFL asks for a modified font.

    python ui/scripts/brand/build_wordmark_font.py RozhaOne-Regular.ttf \
        siddha_wordmark.ttf siddha-mark.woff2

Rozha One: https://github.com/google/fonts/tree/main/ofl/rozhaone
Outputs go to ui/src/assets/fonts/, firebase-public/fonts/ and
ui/android/app/src/main/res/font/.
"""
import sys
from fontTools.ttLib import TTFont
from fontTools import subset
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
src, out_ttf, out_woff2 = sys.argv[1:4]
f = TTFont(src)
opts = subset.Options(); opts.layout_features=['kern','liga']; opts.name_IDs=['*']; opts.notdef_outline=True
s = subset.Subsetter(opts); s.populate(unicodes=range(0x20,0x7F)); s.subset(f)
gs = f.getGlyphSet(); cm = f.getBestCmap(); glyf = f['glyf']
BOT, TOP, OVER = 538, 608, 24
for cp in range(0x20,0x7F):
    ch = chr(cp)
    if not ch.isalpha(): continue
    gn = cm[cp]; w = f['hmtx'][gn][0]
    rec = DecomposingRecordingPen(gs); gs[gn].draw(rec)
    pen = TTGlyphPen(None); rec.replay(pen)
    # clockwise outer contour: the headline bar across the whole advance
    pen.moveTo((-OVER, BOT)); pen.lineTo((-OVER, TOP)); pen.lineTo((w+OVER, TOP)); pen.lineTo((w+OVER, BOT)); pen.closePath()
    g = pen.glyph(); g.flags[0] |= 0x40  # OVERLAP_SIMPLE
    glyf[gn] = g
for gn in glyf.keys():
    glyf[gn].recalcBounds(glyf) if hasattr(glyf[gn],'recalcBounds') else None
name = f['name']
for rec in list(name.names):
    if rec.nameID in (1,4,16,21): name.setName('Siddha Mark' if rec.nameID!=4 else 'Siddha Mark Regular', rec.nameID, rec.platformID, rec.platEncID, rec.langID)
    if rec.nameID in (6,20): name.setName('SiddhaMark-Regular', rec.nameID, rec.platformID, rec.platEncID, rec.langID)
    if rec.nameID == 3: name.setName('SiddhaMark-Regular; modified from Rozha One by 3 Senses Design Studio', 3, rec.platformID, rec.platEncID, rec.langID)
    if rec.nameID == 0: name.setName(str(rec) + ' Modified 2026 by 3 Senses Design Studio: Latin subset with a headline bar on each letter.', 0, rec.platformID, rec.platEncID, rec.langID)
f['head'].recalcBBoxes = True
f.save(out_ttf)
f.flavor = 'woff2'; f.save(out_woff2)
