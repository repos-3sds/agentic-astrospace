"""Build the mantra corpus: mantras.json/.csv and bphs_antardasha_remedies.json/.csv."""
import csv, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from indic_transliteration import sanscript as S
from corpus_data import *  # noqa
from bphs_ad import AD, MISSING_PAGES

OUT = sys.argv[1]
ad_pages = json.load(open(os.path.join(os.path.dirname(__file__), "ad_pages.json")))
ad_pages.update({k: list(v) for k, v in MISSING_PAGES.items()})

def iast(t): return S.transliterate(t, S.DEVANAGARI, S.IAST) if t else None
import re
# Telugu readers write a nasal before a consonant of its own class as anusvara (సంధ్య, not సన్ధ్య).
_TE_NASAL = re.compile("ఙ్(?=[కఖగఘ])|ఞ్(?=[చఛజఝ])|ణ్(?=[టఠడఢ])|న్(?=[తథదధ])|మ్(?=[పఫబభ])")
def telugu(t): return _TE_NASAL.sub("ం", S.transliterate(t, S.DEVANAGARI, S.TELUGU)) if t else None

NO_COMBUST = {"Sun", "Rahu", "Ketu"}
GOCHARA = {"Saturn": ["gochara_sade_sati", "gochara_ashtama_shani", "gochara_kantaka_shani"],
           "Rahu": ["gochara_rahu_moon_caution"], "Ketu": ["gochara_ketu_moon_caution"],
           "Mars": ["gochara_mars_moon_trigger"]}
YOGAS = {"Moon": ["kemadruma_yoga", "shakata_yoga"], "Jupiter": ["guru_chandala_yoga", "shakata_yoga"],
         "Rahu": ["guru_chandala_yoga", "kalasarpa_flag"], "Ketu": ["kalasarpa_flag"]}
DOSHAS = {"Mars": ["dosha-manglik"], "Ketu": ["dosha-gandanta"], "Rahu": ["dosha-grahan"]}
GRAHA_FEST = {"Sun": ["makar_sankranti", "ratha_saptami"], "Saturn": ["shani_jayanti"],
              "Jupiter": ["guru_purnima"], "Moon": ["sharad_purnima"]}
READING = {"Sun": ["career"], "Moon": ["relationship", "spiritual"], "Mars": ["career"],
           "Mercury": ["learning", "career"], "Jupiter": ["learning", "spiritual", "finance"],
           "Venus": ["relationship", "finance"], "Saturn": ["career", "timing"],
           "Rahu": ["timing"], "Ketu": ["spiritual"]}

# BPHS antardasha pairs that cite a mantra id
pairs_for = {}
for (md, ad), (_, ids, _, _) in AD.items():
    for i in ids:
        pairs_for.setdefault(i, []).append(f"{md}-{ad}")

def graha_maps(p, kind):
    rec = [f"dasha-mahadasha-{p.lower()}", f"dasha-antardasha-{p.lower()}", f"dignity-debilitated-{p.lower()}"]
    if p not in NO_COMBUST: rec.append(f"combustion-{p.lower()}")
    rec += DOSHAS.get(p, [])
    if kind == "vedic" and p in ("Sun", "Moon"): rec.append("dosha-grahan")
    return {"practice_slugs": [f"{p.lower()}-mantra"], "recommendation_ids": rec,
            "bphs_antardasha": pairs_for.get(f"{p.lower()}-{kind}", []),
            "gochara_rules": GOCHARA.get(p, []), "yoga_rules": YOGAS.get(p, []),
            "festival_slugs": GRAHA_FEST.get(p, []), "reading_categories": READING.get(p, [])}

def entry(**kw):
    dev = kw.get("devanagari")
    base = {"id": None, "name": None, "category": None, "tier": None, "planet": None, "deity": None,
            "devanagari": dev, "iast": iast(dev), "telugu": telugu(dev), "simple_transliteration": None,
            "meaning_en": None, "source_type": None, "source_citation": None, "kb_citation": None,
            "online_refs": [], "confidence": None, "traditional_count": None, "practical_count": 108,
            "count_note": None, "preferred_day": None, "disagreements": None, "app_sensitivity": None,
            "text_in_corpus": dev is not None, "audio": {"status": "needs_recording", "est_seconds_per_repetition": None,
            "recording_note": None}, "maps_to": {}}
    base.update({k: v for k, v in kw.items() if k != "devanagari"})
    return base

rows = []
for p in PLANETS:
    pl = p.lower()
    dev, simple, meaning = NAMA[p]
    rows.append(entry(id=f"{pl}-nama", name=f"{p} nama mantra", category="graha_nama", tier="simple",
        planet=p, deity=p, devanagari=dev, simple_transliteration=simple, meaning_en=meaning,
        source_type="liturgical", source_citation="Navagraha puja namaskara formula ('om ... namah'); the form the app ships today (astrospace/core/vedic/remedies.py GRAHA_REMEDIES).",
        online_refs=[SD_SUKTA], confidence="verified_attribution", traditional_count=None, practical_count=108,
        count_note="108 per sitting (one mala). No classical count for the nama form; BPHS counts apply to the Vedic mantras.",
        preferred_day=DAYS[p], disagreements=NAMA_NOTES.get(p), maps_to=graha_maps(p, "nama"),
        audio={"status": "needs_recording", "est_seconds_per_repetition": 3, "recording_note": "Loopable single repetition."}))
    dev, simple = BIJA[p]
    rows.append(entry(id=f"{pl}-bija", name=f"{p} bija mantra", category="graha_bija", tier="advanced",
        planet=p, deity=p, devanagari=dev, simple_transliteration=simple,
        meaning_en=f"Om, seed syllables of {p}, salutation to {p}. Bija syllables carry no dictionary meaning.",
        source_type="tantra", source_citation="Tantric navagraha bija mantras as given in ritual manuals (commonly traced to the Mantra Maharnava); no single primary text verified.",
        online_refs=[SD_VEDOKTA, DRIK], confidence="sources_disagree" if p in BIJA_DISAGREE else "popular_tradition",
        traditional_count=BPHS_COUNTS[p], practical_count=108,
        count_note=f"Manuals reuse the BPHS ch.84 count ({BPHS_COUNTS[p]:,}) for the bija form; some multiply by 4 for Kali Yuga. 108 per sitting.",
        preferred_day=DAYS[p], disagreements=BIJA_DISAGREE.get(p),
        app_sensitivity="Bija mantras are traditionally received from a teacher in many lineages. Label 'traditionally taken with guidance'; keep the nama form as default.",
        maps_to=graha_maps(p, "bija"),
        audio={"status": "needs_recording", "est_seconds_per_repetition": 5, "recording_note": "Loopable; nasal endings (anusvara vs candrabindu) audible, so match the chosen text."}))
    dev, ref, meaning = VEDIC[p]
    rows.append(entry(id=f"{pl}-vedic", name=f"{p} Vedic mantra (BPHS)", category="graha_vedic", tier="advanced",
        planet=p, deity=p, devanagari=dev, simple_transliteration=None, meaning_en=meaning,
        source_type="shruti", source_citation=f"{ref}. Named for {p} in BPHS ch.84 (Graha Shanti) vv.17-18; count from v.19.",
        kb_citation=f"{KB_BPHS}, ch.84 vv.17-20, pp.815-816" + ("; also ch.91 (eclipse-birth shanti), p.831" if p in ("Sun", "Moon", "Rahu") else ""),
        online_refs=[SD_VEDOKTA, SD_SUKTA], confidence="verified_text",
        traditional_count=BPHS_COUNTS[p], practical_count=108,
        count_note=("BPHS v.19 says 'dishah' = 10, i.e. 10,000. Santhanam's printed table says 11,000: a translation slip. sanskritdocuments also gives 10,000." if p == "Mars" else
                    "sanskritdocuments 'Vedokta' prayoga gives 4,000 instead of BPHS's 9,000." if p == "Mercury" else
                    f"BPHS ch.84 v.19-20: {BPHS_COUNTS[p]:,}. 108 per sitting.") ,
        preferred_day=DAYS[p],
        disagreements=("VS 9.40 ends 'asyai viśa eṣa vo'mī rājā'; some shanti manuals read 'asyai viśe'. Chanted with Vedic accent the text runs as one long sandhi." if p == "Moon" else None),
        app_sensitivity="Vedic mantra: traditionally learnt with svara (accent) from a teacher, and some traditions restrict it to the initiated. Offer as listen-along audio by a trained reciter; do not machine-voice it.",
        maps_to=graha_maps(p, "vedic"),
        audio={"status": "needs_recording", "est_seconds_per_repetition": 20, "recording_note": "Record with svara by a Shukla Yajurveda reciter; TTS is not acceptable for accented Vedic text."}))
    if p in VEDIC_SOUTH:
        dev, ref, meaning = VEDIC_SOUTH[p]
        rows.append(entry(id=f"{pl}-vedic-taittiriya", name=f"{p} Vedic mantra (Taittiriya / South Indian form)", category="graha_vedic", tier="advanced",
            planet=p, deity=p, devanagari=dev, meaning_en=meaning, source_type="shruti",
            source_citation=f"{ref}. Used in the Navagraha Sukta recited in Telugu, Tamil and Kannada temples (Krishna Yajurveda tradition).",
            online_refs=[SD_SUKTA], confidence="sources_disagree", traditional_count=BPHS_COUNTS[p], practical_count=108,
            count_note="Same counts are applied by custom; BPHS itself names the Shukla Yajurveda verse.",
            preferred_day=DAYS[p],
            disagreements=f"BPHS ch.84 names a different verse for {p} (see {pl}-vedic). Both are authentic; which one a family uses depends on its Veda shakha. Checked against sanskritdocuments: differences are sandhi only.",
            app_sensitivity="As for the Shukla Yajurveda form: accented, teacher-learnt; listen-along audio only.",
            maps_to=graha_maps(p, "vedic"),
            audio={"status": "needs_recording", "est_seconds_per_repetition": 20, "recording_note": "Record with Krishna Yajurveda svara."}))
    dev, simple, meaning = STOTRA[p]
    rows.append(entry(id=f"{pl}-stotra", name=f"{p} verse, Navagraha Stotra", category="graha_stotra", tier="simple",
        planet=p, deity=p, devanagari=dev, simple_transliteration=simple, meaning_en=meaning,
        source_type="stotra", source_citation="Navagraha Stotra, attributed by tradition to Vyasa (colophon: 'iti śrīvyāsaviracitaṃ navagrahastotram'). Not located in a specific Purana.",
        online_refs=[SD_STOTRA], confidence="verified_text", traditional_count=None, practical_count=11,
        count_note="Recited once, 3 or 11 times; the whole 9-verse stotra once daily is common.",
        preferred_day=DAYS[p], disagreements="Orthography only: sanskritdocuments writes anusvara (संकाश, संभव) where this corpus writes the nasal conjunct (सङ्काश, सम्भव). Same pronunciation.",
        maps_to=graha_maps(p, "stotra"),
        audio={"status": "needs_recording", "est_seconds_per_repetition": 10, "recording_note": "Unaccented; a clear Sanskrit voice is enough."}))

for d in DEITY:
    planets = [p for p, ids in APP_DEITY.items() if d["id"] in ids]
    rows.append(entry(id=d["id"], name=d["name"], category="deity_or_text" if d["dev"] else "recitation_reference",
        tier="simple" if d["conf"] != "popular_tradition" or d["dev"] else "simple",
        planet=None, deity=d["deity"], devanagari=d["dev"], simple_transliteration=d["simple"], meaning_en=d["meaning"],
        source_type=d["stype"], source_citation=d["cite"], confidence=d["conf"], traditional_count=d["trad"],
        practical_count=d["prac"], count_note=d["cnote"], disagreements=d["dis"], app_sensitivity=d["sens"],
        maps_to={"practice_slugs": [f"{p.lower()}-deity" for p in planets], "app_deity_for": planets,
                 "bphs_antardasha": pairs_for.get(d["id"], [])},
        audio={"status": "needs_recording" if d["dev"] else "long_form_reference",
               "est_seconds_per_repetition": d["secs"],
               "recording_note": "Long text: offer as a single listen-along track, not a counter." if not d["dev"] else None}))

# festival, yoga, gochara and reading mappings for deity mantras
FEST = {
 "ganesha-nama": ["ganesh_chaturthi", "anant_chaturdashi"], "ganesha-vakratunda": ["ganesh_chaturthi"],
 "shiva-panchakshari": ["maha_shivaratri", "kartika_purnima", "arudra_darshan"], "mahamrityunjaya": ["maha_shivaratri"],
 "sri-rudram": ["maha_shivaratri"], "vishnu-dvadashakshari": ["krishna_janmashtami", "vaikuntha_ekadashi", "devshayani_ekadashi", "devutthana_ekadashi", "gita_jayanti", "nirjala_ekadashi", "putrada_ekadashi"],
 "vishnu-sahasranama": ["vaikuntha_ekadashi", "anant_chaturdashi"], "rama-taraka": ["rama_navami", "sita_navami"],
 "rama-nama-sahasranama-tulya": ["rama_navami"], "lakshmi-nama": ["diwali", "dhanteras", "varalakshmi_vratam", "sharad_purnima", "akshaya_tritiya"],
 "sri-suktam-1": ["diwali", "varalakshmi_vratam"], "hanuman-nama": ["hanuman_jayanti", "hanumath_jayanti_south"],
 "hanuman-manojavam": ["hanuman_jayanti", "hanumath_jayanti_south"], "hanuman-chalisa": ["hanuman_jayanti"],
 "sarpa-namostu": ["nag_panchami", "nagula_chavithi"], "guru-vandana": ["guru_purnima", "shankara_jayanti"],
 "saraswati-vidyarambha": ["vasant_panchami"], "saraswati-nama": ["vasant_panchami", "ayudha_puja"],
 "durga-navarna": ["navratri_begins", "chaitra_navratri", "durga_ashtami", "ayudha_puja", "vijayadashami"],
 "durga-sarvamangala": ["navratri_begins", "chaitra_navratri", "durga_ashtami", "vijayadashami", "gauri_habba", "hartalika_teej"],
 "durga-saptashati": ["navratri_begins", "chaitra_navratri", "durga_ashtami"],
 "aditya-hridayam": ["makar_sankranti", "ratha_saptami", "chhath"], "surya-dvadasha-nama": ["ratha_saptami", "makar_sankranti", "chhath"],
 "gayatri": ["avani_avittam"], "skanda-shadakshari": ["skanda_sashti", "thai_poosam", "subrahmanya_shashthi", "panguni_uthiram"],
}
READ = {"mahamrityunjaya": ["health", "spiritual"], "aditya-hridayam": ["career", "health"], "lakshmi-nama": ["finance"],
        "sri-suktam-1": ["finance"], "durga-sarvamangala": ["relationship"], "saraswati-vidyarambha": ["learning"],
        "saraswati-nama": ["learning"], "ganesha-nama": ["learning", "career"], "gayatri": ["spiritual", "learning"],
        "shiva-panchakshari": ["spiritual"], "vishnu-dvadashakshari": ["spiritual"], "hanuman-manojavam": ["career"]}
YOGA_D = {"shiva-panchakshari": ["kemadruma_yoga", "kalasarpa_flag"], "sarpa-namostu": ["kalasarpa_flag"],
          "mahamrityunjaya": ["kalasarpa_flag"], "durga-sarvamangala": ["guru_chandala_yoga"]}
GOCH_D = {"hanuman-manojavam": ["gochara_sade_sati", "gochara_ashtama_shani", "gochara_kantaka_shani", "gochara_mars_moon_trigger"],
          "hanuman-chalisa": ["gochara_sade_sati", "gochara_ashtama_shani", "gochara_kantaka_shani"],
          "durga-sarvamangala": ["gochara_rahu_moon_caution"], "ganesha-nama": ["gochara_ketu_moon_caution"]}
DOSHA_D = {"ganesha-nama": ["dosha-gandanta"], "durga-sarvamangala": ["dosha-grahan"], "hanuman-manojavam": ["dosha-manglik"]}
for r in rows:
    if r["category"].startswith("graha"): continue
    m = r["maps_to"]
    m["festival_slugs"] = FEST.get(r["id"], []); m["reading_categories"] = READ.get(r["id"], [])
    m["yoga_rules"] = YOGA_D.get(r["id"], []); m["gochara_rules"] = GOCH_D.get(r["id"], [])
    m["recommendation_ids"] = DOSHA_D.get(r["id"], [])

# Every verse text is keyed from a public-domain print (pre-1931), page by page;
# see rekey/transcriptions.tsv and docs/mantra_corpus.md. The print's text,
# normalised to corpus spelling, replaces the text in corpus_data.
from rekey.normalise import normalise
REKEY_DIR = os.path.join(os.path.dirname(__file__), "rekey")
EDITIONS = json.load(open(os.path.join(REKEY_DIR, "editions.json"), encoding="utf-8"))
SCAN = "https://archive.org/details/{}/page/n{}/mode/1up"
# 'Om' is said before these two but is not part of the printed verse.
RECITER_PREFIX = {"gayatri": "ॐ ", "mahamrityunjaya": "ॐ "}
REKEY = {}
for line in open(os.path.join(REKEY_DIR, "transcriptions.tsv"), encoding="utf-8"):
    if line.startswith("#") or not line.strip(): continue
    vid, ed, leaf, page, text, note = line.rstrip("\n").split("\t")
    REKEY[vid] = (RECITER_PREFIX.get(vid, "") + normalise(text.replace("\\n", " ")),
                  {"kind": "print", "edition": ed, "scan_page_url": SCAN.format(EDITIONS[ed]["archive_id"], leaf),
                   "page": page or None, "note": note})

FORMULA = ("A short devotional formula (a name with a salutation or seed syllables), not a verse; "
           "no edition text to key it from.")
FORMULAS = {"shiva-panchakshari", "vishnu-dvadashakshari", "durga-navarna", "durga-nama", "lakshmi-nama",
            "ganesha-nama", "hanuman-nama", "saraswati-nama", "rama-taraka", "skanda-shadakshari", "surya-dvadasha-nama"}
NOT_LOCATED = {
 "sri-suktam-1": "The Sri Sukta is a Rigveda khila; no pre-1931 print of it was found in this pass (Scheftelowitz 1906 is the candidate).",
 "ganesha-vakratunda": "A popular invocation; no pre-1931 print was found in this pass.",
 "saraswati-vidyarambha": "A popular verse said before study; no pre-1931 print was found in this pass.",
 "santana-gopala": "BPHS names the mantra without its text; no pre-1931 print of this verse was found in this pass.",
}
for r in rows:
    if r["id"] in REKEY:
        dev, prov = REKEY[r["id"]]
        r.update(devanagari=dev, iast=iast(dev), telugu=telugu(dev), provenance=prov)
    elif r["id"] in NOT_LOCATED:
        r["provenance"] = {"kind": "no_print_located", "note": NOT_LOCATED[r["id"]]}
    elif r["devanagari"] is None:
        r["provenance"] = {"kind": "reference_only", "note": "Named as a practice; the corpus ships no text for it."}
    else:
        assert r["category"] in ("graha_nama", "graha_bija") or r["id"] in FORMULAS, f"{r['id']} has no print transcription"
        r["provenance"] = {"kind": "formula", "note": FORMULA}
    if r["id"] == "jupiter-vedic": r["disagreements"] = "Some modern Vajasaneyi editions read 'yadaryā arhād'; Weber's 1852 print reads 'yadaryo arhād', as the Rigveda does."
    if r["id"].endswith("-vedic-taittiriya"):
        r["disagreements"] = r["disagreements"].replace(" Checked against sanskritdocuments: differences are sandhi only.", "")

from meanings_i18n import MEANINGS, bija as bija_meaning
for r in rows:
    if r["id"] in VEDIC_SIMPLE: r["simple_transliteration"] = VEDIC_SIMPLE[r["id"]]
    hi_te = bija_meaning(r["planet"]) if r["category"] == "graha_bija" else MEANINGS[r["id"]]
    r["meaning_hi"], r["meaning_te"] = hi_te
    # The three scripts the app shows the mantra in: Telugu, English letters, Devanagari (Sanskrit/Hindi).
    r["text"] = {"te": r["telugu"], "en": r["simple_transliteration"], "sa": r["devanagari"], "iast": r["iast"]} if r["devanagari"] else None

ids = {r["id"] for r in rows}
for (md, ad), (_, mids, _, _) in AD.items():
    for i in mids: assert i in ids, (md, ad, i)

os.makedirs(OUT, exist_ok=True)
meta = {"name": "Siddha mantra corpus", "version": "2026-10-19", "editions": EDITIONS, "status": "point-in-time research corpus; not yet wired into the app",
        "fields": "see README.md", "count": len(rows)}
json.dump({"meta": meta, "mantras": rows}, open(f"{OUT}/mantras.json", "w"), ensure_ascii=False, indent=1)
cols = ["id", "name", "category", "tier", "planet", "deity", "devanagari", "iast", "telugu", "simple_transliteration",
        "meaning_en", "meaning_hi", "meaning_te", "source_type", "source_citation", "kb_citation", "confidence", "traditional_count", "practical_count",
        "count_note", "preferred_day", "disagreements", "app_sensitivity", "provenance_kind", "provenance_page_url", "practice_slugs", "recommendation_ids",
        "bphs_antardasha", "gochara_rules", "yoga_rules", "festival_slugs", "reading_categories", "audio_status", "audio_est_seconds"]
with open(f"{OUT}/mantras.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(cols)
    for r in rows:
        flat = dict(r)
        flat.update({k: "|".join(v) for k, v in r["maps_to"].items()})
        flat["provenance_kind"] = r["provenance"]["kind"]
        flat["provenance_page_url"] = r["provenance"].get("scan_page_url", "")
        flat["audio_status"] = r["audio"]["status"]
        flat["audio_est_seconds"] = r["audio"]["est_seconds_per_repetition"]
        w.writerow([flat.get(c, "") for c in cols])

adrows = []
for (md, ad), (says, mids, charity, note) in AD.items():
    ch, pg = ad_pages[f"{md}-{ad}"]
    adrows.append({"mahadasha": md, "antardasha": ad, "recommendation_ids": [f"dasha-mahadasha-{md.lower()}", f"dasha-antardasha-{ad.lower()}"],
                   "bphs_prescription": says, "mantra_ids": mids, "charity": charity, "note": note,
                   "kb_citation": f"{KB_BPHS}, ch.{ch}, p.{pg}"})
json.dump({"meta": {"source": KB_BPHS, "chapters": "52-60 (Vimshottari antardasha effects)",
                    "caveat": "BPHS gives these remedies for the adverse case of each sub-period, often framed as averting illness or death. The app must show them as traditional practices for the period, never with that framing."},
           "rows": adrows}, open(f"{OUT}/bphs_antardasha_remedies.json", "w"), ensure_ascii=False, indent=1)
with open(f"{OUT}/bphs_antardasha_remedies.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["mahadasha", "antardasha", "bphs_prescription", "mantra_ids", "charity", "note", "kb_citation"])
    for r in adrows: w.writerow([r["mahadasha"], r["antardasha"], r["bphs_prescription"], "|".join(r["mantra_ids"]), r["charity"] or "", r["note"] or "", r["kb_citation"]])
print(len(rows), "mantras;", len(adrows), "antardasha rows;", sum(1 for r in adrows if r["mantra_ids"]), "with a mantra")
