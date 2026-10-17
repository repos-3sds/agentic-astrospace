import json, sys
OUT = sys.argv[1]
d = json.load(open(f"{OUT}/mantras.json"))["mantras"]
ad = json.load(open(f"{OUT}/bphs_antardasha_remedies.json"))["rows"]
byid = {r["id"]: r for r in d}
L = ["# Mantra catalogue", "", "**Status: point-in-time research catalogue (2026-10-17).** Generated from `mantras.json` by `scripts/build_catalogue.py`; edit the data, not this file.", ""]
def sec(title, rows):
    L.append(f"## {title}"); L.append("")
    for r in rows:
        L.append(f"### {r['name']}  `{r['id']}`"); L.append("")
        if r["devanagari"]:
            t = r["text"]
            L.append(f"> **తెలుగు:** {t['te']}"); L.append(">")
            L.append(f"> **English:** {t['en']}"); L.append(">")
            L.append(f"> **संस्कृत / हिन्दी:** {t['sa']}"); L.append(">")
            L.append(f"> *IAST: {t['iast']}*"); L.append("")
        L.append(f"**Meaning.** {r['meaning_en']}"); L.append("")
        L.append(f"**అర్థం.** {r['meaning_te']}"); L.append("")
        L.append(f"**अर्थ.** {r['meaning_hi']}"); L.append("")
        L.append(f"**Source.** {r['source_citation']}" + (f" KB: {r['kb_citation']}." if r.get('kb_citation') else "")); L.append("")
        cnt = f"{r['traditional_count']:,} traditional; " if r.get("traditional_count") else ""
        L.append(f"**Count.** {cnt}{r['practical_count']} per sitting. {r['count_note'] or ''}"); L.append("")
        L.append(f"**Confidence.** `{r['confidence']}`. {r.get('checked_against','')}"); L.append("")
        if r.get("disagreements"): L.append(f"**Sources disagree.** {r['disagreements']}"); L.append("")
        if r.get("app_sensitivity"): L.append(f"**App care.** {r['app_sensitivity']}"); L.append("")
        m = r["maps_to"]; parts = []
        for k, lab in [("practice_slugs","practice"),("recommendation_ids","remedy trigger"),("bphs_antardasha","BPHS dasha-bhukti"),("gochara_rules","transit"),("yoga_rules","yoga"),("festival_slugs","festival"),("reading_categories","reading")]:
            if m.get(k): parts.append(f"{lab}: " + ", ".join(f"`{x}`" for x in m[k]))
        if parts: L.append("**Maps to.** " + "; ".join(parts)); L.append("")
for title, cat in [("1. Graha nama mantras (simple, what the app ships)", "graha_nama"), ("2. Navagraha Stotra verses (simple)", "graha_stotra"),
                   ("3. Vedic graha mantras from BPHS ch.84 (advanced)", "graha_vedic"), ("4. Bija mantras (advanced)", "graha_bija")]:
    sec(title, [r for r in d if r["category"] == cat])
sec("5. Deity mantras and short texts", [r for r in d if r["category"] == "deity_or_text"])
sec("6. Long recitations (reference entries, audio only)", [r for r in d if r["category"] == "recitation_reference"])
L += ["## 7. BPHS remedy for every dasha and bhukti", "", "Santhanam tr. ch.52-60. 'Mantras' lists corpus ids. BPHS gives these for the adverse case, often framed around illness or death: show them as traditional practice for the period only.", "",
      "| Mahadasha | Antardasha | BPHS prescribes | Mantras | Page |", "|---|---|---|---|---|"]
for r in ad:
    L.append(f"| {r['mahadasha']} | {r['antardasha']} | {r['bphs_prescription']}{' ('+r['note']+')' if r['note'] else ''} | {', '.join(r['mantra_ids']) or '—'} | {r['kb_citation'].split(', ')[-1]} |")
open(f"{OUT}/catalogue.md", "w").write("\n".join(L) + "\n")
print(len(L), "lines")
