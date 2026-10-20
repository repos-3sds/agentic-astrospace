"""What to do on each festival and vrat day, for the Calendar's festival sheet.

Kept apart from ``festivals.py`` so the date rules there stay scannable. Every
entry is deliberately small (Hawk, 2026-10-20: "grounded, simple and accurate,
not overwhelming"):

* ``todo``: two to four short steps, the plain core of the day.
* ``how``: one line on when or how, the detail people most often get wrong.
* ``mantras``: at most two prayers to recite, **by name only**. A name with a
  corpus id points at ``mantra_corpus/mantras.json``, where the app already
  holds the text; the rest are well-known stotras named as suggestions. No
  verse text lives here, so nothing here needs a pre-1931 print (D12).

House rules for the copy: simple English for Indian readers (see
``agents/style.py``), no fear, nothing costly, the family's custom first, and
a fast only "if your health allows". Regional ways get one step, not a list.
"""

# (display name, corpus id or None)
Mantra = tuple[str, str | None]

FESTIVAL_GUIDANCE: dict[str, dict] = {}
VRAT_GUIDANCE: dict[str, dict] = {}


def _g(slug: str, todo: list[str], how: str, mantras: list[Mantra],
       table: dict | None = None) -> None:
    (FESTIVAL_GUIDANCE if table is None else table)[slug] = {
        "todo": todo, "how": how, "mantras": mantras,
    }


# ── Chaitra ──────────────────────────────────────────────────────────────────
_g("ugadi",
   ["Take an oil bath and wear clean or new clothes.",
    "Make Ugadi pachadi with six tastes: neem flower, jaggery, tamarind, "
    "raw mango, salt and chilli.",
    "Listen to the new year's panchangam reading (Panchanga Shravanam).",
    "In Maharashtra, raise a Gudi at the door."],
   "Morning, after sunrise. Eat a little pachadi before the meal.",
   [("Om Gam Ganapataye Namah", "ganesha-nama"),
    ("Vishnu Sahasranama", "vishnu-sahasranama")])
_g("gauri_habba",
   ["Worship Gauri and Shiva (Isar) with flowers and kumkum.",
    "Women sing Gangaur songs and carry the idols to water in the evening.",
    "Share sweets with friends and neighbours."],
   "Gangaur closes 18 days of worship that begin the day after Holi.",
   [("Sarva Mangala Mangalye", "durga-sarvamangala"),
    ("Gauri Ashtottara Shatanamavali", None)])
_g("rama_navami",
   ["Do a simple puja to Sita and Rama around noon.",
    "Offer panakam (jaggery water) and vada pappu or kosambari.",
    "Read a little of the Ramayana, or listen to a Sita Rama Kalyanam."],
   "Rama was born at midday, so noon is the main puja time.",
   [("Sri Rama Jaya Rama", "rama-taraka"),
    ("Rama Raksha Stotram", None)])
_g("hanuman_jayanti",
   ["Visit a Hanuman temple, or light a lamp at home.",
    "Recite or listen to the Hanuman Chalisa.",
    "Offer what is simple: betel leaves, a flower garland or jaggery."],
   "Morning puja. Telugu homes keep Hanuman Jayanti on a different day, in Vaishakha.",
   [("Hanuman Chalisa", "hanuman-chalisa"),
    ("Manojavam Marutatulyavegam", "hanuman-manojavam")])

# ── Solar new year ───────────────────────────────────────────────────────────
_g("tamil_puthandu",
   ["Kerala and many Tamil homes set out fruit, flowers and a mirror the night before (Kani).",
    "Take an early bath and visit a temple or pray at home.",
    "Listen to the new year's panchangam reading.",
    "Kerala gives Vishu kaineettam (a small gift) to children; Punjab goes to the gurudwara for Baisakhi."],
   "The Kani is seen first thing on waking, before anything else.",
   [("Om Suryaya Namah", "sun-nama"),
    ("Vishnu Sahasranama", "vishnu-sahasranama")])

# ── Vaishakha ────────────────────────────────────────────────────────────────
_g("akshaya_tritiya",
   ["Give something useful: water, buttermilk, food or a hand fan in the summer heat.",
    "A good day to start a new habit, study or work.",
    "Buying gold is a custom, not a need. A small act of charity is enough."],
   "Any time in the day; morning puja is common.",
   [("Om Shreem Mahalakshmyai Namah", "lakshmi-nama"),
    ("Kanakadhara Stotram", None)])
_g("narasimha_jayanti",
   ["Many keep a light fast until evening, if health allows.",
    "Do a short puja to Narasimha at dusk.",
    "Offer panakam (jaggery water) and share it."],
   "Narasimha appeared at dusk, so the main puja is around sunset.",
   [("Lakshmi Narasimha Karavalamba Stotram", None),
    ("Vishnu Sahasranama", "vishnu-sahasranama")])
_g("buddha_purnima",
   ["Visit a vihara or sit quietly for a few minutes.",
    "Do one kind act: feed someone, or help an animal.",
    "Hindu homes also mark Kurma Jayanti today with a Vishnu prayer."],
   "Any time in the day; full moon evening is also kept.",
   [("Buddham Saranam Gacchami (the Three Refuges)", None)])

# ── Jyeshtha ─────────────────────────────────────────────────────────────────
_g("vat_savitri",
   ["Pray at a banyan tree and wind a thread around it.",
    "Read or hear the story of Savitri and Satyavan.",
    "Fast only if your health allows. A simple meal also counts.",
    "Maharashtra, Gujarat and Karnataka keep it on the full moon instead (Vat Purnima)."],
   "Morning puja. The fast ends after the puja or in the evening, by family custom.",
   [("Sarva Mangala Mangalye", "durga-sarvamangala")])
_g("ganga_dussehra",
   ["Take a bath, in the Ganga or any river if near; at home is fine.",
    "Offer water and a lamp to the river or a pot of water.",
    "Give water, fruit or curd rice to those who need it in the heat."],
   "Morning bath; lamp in the evening.",
   [("Ganga Stotram", None)])

# ── Ashadha ──────────────────────────────────────────────────────────────────
_g("rath_yatra",
   ["Watch the chariot pull at Puri, or at a local ISKCON or Jagannath temple.",
    "Offer a simple sweet at home.",
    "Sing or listen to Jagannath bhajans."],
   "The chariots roll in the afternoon at Puri.",
   [("Jagannath Ashtakam", None),
    ("Om Namo Bhagavate Vasudevaya", "vishnu-dvadashakshari")])
_g("guru_purnima",
   ["Thank a teacher, parent or elder in person or by phone.",
    "Read a little from a book that taught you something.",
    "Many offer a flower or fruit to their guru's picture."],
   "Morning is common. Also called Vyasa Purnima.",
   [("Gurur Brahma", "guru-vandana"),
    ("Om Gurave Namah", "jupiter-nama")])

# ── Shravana ─────────────────────────────────────────────────────────────────
_g("nag_panchami",
   ["Pray to a snake image, a temple idol or an anthill.",
    "Offer flowers, turmeric and a little milk to the image only.",
    "Never give milk to a live snake or disturb one; it harms them."],
   "Morning, at home or the temple.",
   [("Namostu Sarpebhyah", "sarpa-namostu")])
_g("varalakshmi_vratam",
   ["Set up a kalasham the evening before and decorate it as Lakshmi.",
    "Do the puja in the morning and tie the yellow thread (thoram).",
    "Give tamboolam (betel, turmeric, kumkum, fruit) to married women.",
    "New jewellery is not needed. Flowers and devotion are enough."],
   "Morning puja on the Friday. Read the vrata katha after the puja.",
   [("Lakshmi Ashtottara Shatanamavali", None),
    ("Om Shreem Mahalakshmyai Namah", "lakshmi-nama")])
_g("raksha_bandhan",
   ["Sisters tie a rakhi and apply tilak; brothers give a gift and a promise of care.",
    "Share sweets as a family.",
    "Tie the rakhi outside the Bhadra time if your family follows it."],
   "After the morning puja; check the Bhadra time in your panchangam.",
   [("Yena Baddho Bali Raja (the rakhi prayer)", None)])
_g("krishna_janmashtami",
   ["Many fast until midnight, if health allows. Fruit and milk also count.",
    "Decorate a cradle for baby Krishna.",
    "Offer butter, curd or a milk sweet at midnight.",
    "South homes draw small footprints at the door; Maharashtra has Dahi Handi."],
   "Krishna was born at midnight, so the main puja is at midnight.",
   [("Om Namo Bhagavate Vasudevaya", "vishnu-dvadashakshari"),
    ("Madhurashtakam", None)])

# ── Bhadrapada ───────────────────────────────────────────────────────────────
_g("ganesh_chaturthi",
   ["Bring a clay Ganesha; avoid plaster of Paris and plastic.",
    "Offer patri (leaves), durva grass and modak or undrallu.",
    "Read or hear the Vinayaka vrata katha.",
    "Immerse the idol in a bucket at home or a tank set up for it."],
   "Morning or midday puja. Many keep 1.5, 3, 5, 7 or 10 days.",
   [("Om Gam Ganapataye Namah", "ganesha-nama"),
    ("Vakratunda Mahakaya", "ganesha-vakratunda")])
_g("onam",
   ["Make a pookalam (flower carpet) at the door.",
    "Cook or share an Onasadya on a banana leaf.",
    "Wear new or clean clothes and spend the day with family."],
   "Pookalam begins on Atham, ten days before; Thiruvonam is the main day.",
   [("Om Namo Narayanaya", None)])
_g("mahalaya_amavasya",
   ["Remember your ancestors by name.",
    "Offer tarpanam (water and sesame) if your family does it; a priest can guide.",
    "Feed someone in need, or a cow or crows.",
    "In Bengal, many listen to the Mahishasura Mardini recital at dawn."],
   "Tarpanam is done in the late morning or midday, not after sunset.",
   [("Om Namo Bhagavate Vasudevaya", "vishnu-dvadashakshari")])

# ── Ashwina ──────────────────────────────────────────────────────────────────
_g("navratri_begins",
   ["Set up the kalash (Ghatasthapana), or light a lamp to keep for nine days.",
    "Pray to the Devi each day, in one of her nine forms.",
    "Fast only if your health allows. A simple meal also counts.",
    "Regional ways: Golu dolls in the South, Bathukamma in Telangana, Garba in Gujarat."],
   "Kalash is set in the morning on the first day.",
   [("Sarva Mangala Mangalye", "durga-sarvamangala"),
    ("Lalitha Sahasranama", None)])
_g("durga_ashtami",
   ["Do the Devi puja in the morning.",
    "Many feed young girls (Kanya puja) and give them a small gift.",
    "In Bengal, Sandhi Puja is done where Ashtami meets Navami."],
   "Morning puja. Some keep Kanya puja on Navami instead.",
   [("Sarva Mangala Mangalye", "durga-sarvamangala"),
    ("Durga Saptashati (reading)", "durga-saptashati")])
_g("ayudha_puja",
   ["Clean your tools, vehicle, books and devices.",
    "Place them before the deity with turmeric, kumkum and a flower.",
    "Rest them for the day; take them up again on Vijayadashami."],
   "Morning puja.",
   [("Om Aim Saraswatyai Namah", "saraswati-nama"),
    ("Sarva Mangala Mangalye", "durga-sarvamangala")])
_g("vijayadashami",
   ["A good day to start learning: children write their first letters (Vidyarambham).",
    "Take up the tools and books kept for puja.",
    "Exchange Shami (Jammi, Banni) leaves with elders and friends.",
    "North India burns Ravana effigies; Bengal says goodbye to Durga."],
   "Morning for Vidyarambham; Shami puja in the afternoon or evening.",
   [("Saraswati Namastubhyam", "saraswati-vidyarambha"),
    ("Sarva Mangala Mangalye", "durga-sarvamangala")])
_g("sharad_purnima",
   ["Make rice kheer and keep it in the moonlight for a while.",
    "Offer a lamp to Lakshmi and the moon.",
    "In Bengal and Odisha this is Kojagari Lakshmi Puja."],
   "Evening, after moonrise.",
   [("Om Chandraya Namah", "moon-nama"),
    ("Om Shreem Mahalakshmyai Namah", "lakshmi-nama")])
_g("karva_chauth",
   ["Eat sargi (a light meal) before sunrise.",
    "Hear the Karva Chauth katha with other women in the evening.",
    "Break the fast after seeing the moon.",
    "Fast only if your health allows. Water or fruit is fine."],
   "The fast ends at moonrise; check the moonrise time for your city.",
   [("Om Namah Shivaya", "shiva-panchakshari"),
    ("Sarva Mangala Mangalye", "durga-sarvamangala")])

# ── Kartika (Diwali cluster) ─────────────────────────────────────────────────
_g("dhanteras",
   ["Clean the house and light a lamp at the main door.",
    "Pray to Dhanvantari for good health in the family.",
    "Buying a small steel vessel is a custom. Gold is not needed."],
   "Evening, after sunset. Many also light one lamp facing south (Yama deepam).",
   [("Om Namo Bhagavate Dhanvantaraye", None),
    ("Om Shreem Mahalakshmyai Namah", "lakshmi-nama")])
_g("naraka_chaturdashi",
   ["Take an oil bath before sunrise.",
    "Wear new or clean clothes and light lamps.",
    "In the South this is the main Deepavali day."],
   "The oil bath is before dawn; lamps in the evening.",
   [("Om Namo Bhagavate Vasudevaya", "vishnu-dvadashakshari")])
_g("diwali",
   ["Clean the home and draw a rangoli at the door.",
    "Light diyas at dusk, and do Lakshmi and Ganesha puja.",
    "Share sweets with neighbours and those who work for you.",
    "Go easy on crackers, for elders, children, pets and the air."],
   "Lakshmi Puja is in the evening (pradosh time). Bengal does Kali Puja tonight.",
   [("Om Shreem Mahalakshmyai Namah", "lakshmi-nama"),
    ("Mahalakshmi Ashtakam", None)])
_g("govardhan_puja",
   ["Cook a few simple dishes and offer them as Annakut.",
    "Pray to Krishna; some make a small Govardhan hill of cow dung or clay.",
    "Maharashtra and Karnataka mark Bali Pratipada; Gujarat its new year."],
   "Morning or midday.",
   [("Om Namo Bhagavate Vasudevaya", "vishnu-dvadashakshari")])
_g("bhai_dooj",
   ["Sisters apply tilak and pray for their brothers' well-being.",
    "Brothers visit, share a meal, and give a gift.",
    "Called Bhau Beej in Maharashtra and Bhai Phonta in Bengal."],
   "Late morning or afternoon is common.",
   [])
_g("chhath",
   ["Day 1 Nahay Khay: bath and one clean meal. Day 2 Kharna: kheer at night.",
    "Day 3: offer arghya (water) to the setting sun at a river or pond.",
    "Day 4: offer arghya to the rising sun, then break the fast.",
    "The fast is strict. Keep it only if your health allows."],
   "Evening arghya at sunset; morning arghya at sunrise.",
   [("Aditya Hridayam", "aditya-hridayam"),
    ("Om Suryaya Namah", "sun-nama")])
_g("tulsi_vivah",
   ["Decorate the Tulsi plant like a bride.",
    "Do the wedding of Tulsi with Krishna or a Shaligram.",
    "Share sweets; this opens the wedding season."],
   "Evening. Some keep it on Ekadashi, some on Dwadashi.",
   [("Om Namo Bhagavate Vasudevaya", "vishnu-dvadashakshari"),
    ("Tulasi Stotram", None)])
_g("kartika_purnima",
   ["Light lamps at home, a temple or by water.",
    "Bathe early, in a river if you can.",
    "Telugu homes light a lamp of 365 wicks; Varanasi lights the ghats (Dev Deepawali)."],
   "Morning bath; lamps after sunset.",
   [("Om Namah Shivaya", "shiva-panchakshari"),
    ("Lingashtakam", None)])
_g("karthigai_deepam",
   ["Light rows of small clay lamps (agal vilakku) at the door and windows.",
    "Offer pori urundai or appam.",
    "Watch the Maha Deepam at Tiruvannamalai, in person or on TV."],
   "Lamps after sunset.",
   [("Om Namah Shivaya", "shiva-panchakshari"),
    ("Om Saravanabhavaya Namah", "skanda-shadakshari")])

# ── Margashirsha / Pausha ────────────────────────────────────────────────────
_g("gita_jayanti",
   ["Read one chapter of the Bhagavad Gita, or a few verses.",
    "Many keep the Ekadashi fast, if health allows.",
    "Share a Gita or a verse with someone."],
   "Any time; morning is common.",
   [("Bhagavad Gita (one chapter)", None),
    ("Om Namo Bhagavate Vasudevaya", "vishnu-dvadashakshari")])
_g("vaikuntha_ekadashi",
   ["Visit a Vishnu temple at dawn and pass through the north gate (Vaikuntha Dwaram).",
    "Keep the Ekadashi fast if your health allows; skip rice at least.",
    "Many stay awake at night with bhajans."],
   "Temple gates open before dawn. Break the fast the next morning.",
   [("Vishnu Sahasranama", "vishnu-sahasranama"),
    ("Om Namo Bhagavate Vasudevaya", "vishnu-dvadashakshari")])

# ── Makara Sankranti ─────────────────────────────────────────────────────────
_g("makar_sankranti",
   ["Take an early bath and pray to the Sun.",
    "Cook pongal or khichdi with new rice; share til and jaggery sweets.",
    "Give food, sesame or a blanket to someone in need.",
    "Fly kites safely: no glass-coated manja, and watch for birds."],
   "Morning, facing the sunrise.",
   [("Om Suryaya Namah", "sun-nama"),
    ("Aditya Hridayam", "aditya-hridayam")])

# ── Magha ────────────────────────────────────────────────────────────────────
_g("vasant_panchami",
   ["Pray to Saraswati; keep books and instruments near her.",
    "Wear yellow if you like, and offer a yellow sweet.",
    "Small children often begin writing letters today (Aksharabhyasam)."],
   "Morning puja.",
   [("Saraswati Namastubhyam", "saraswati-vidyarambha"),
    ("Om Aim Saraswatyai Namah", "saraswati-nama")])
_g("ratha_saptami",
   ["Bathe at sunrise with seven arka (jilledu, erukku) leaves on the head.",
    "Offer water to the Sun.",
    "Cook a sweet pongal or paramannam and offer it."],
   "At sunrise.",
   [("Aditya Hridayam", "aditya-hridayam"),
    ("Twelve names of Surya", "surya-dvadasha-nama")])
_g("thai_poosam",
   ["Visit a Murugan temple or pray at home.",
    "Offer milk, fruit or panchamritam.",
    "Kavadi and piercing are personal vows, never needed."],
   "Morning puja.",
   [("Om Saravanabhavaya Namah", "skanda-shadakshari"),
    ("Kanda Sashti Kavacham", None)])
_g("magha_purnima",
   ["Take an early bath, in a river if you can.",
    "Give food or warm clothes to someone in need.",
    "Many families keep the Satyanarayana puja on a full moon."],
   "Early morning bath.",
   [("Om Namo Bhagavate Vasudevaya", "vishnu-dvadashakshari")])

# ── Phalguna ─────────────────────────────────────────────────────────────────
_g("maha_shivaratri",
   ["Offer water or milk and bilva leaves to a Shiva linga.",
    "Keep a fast if your health allows; fruit and milk also count.",
    "Stay up for part of the night with Om Namah Shivaya. One part is enough."],
   "The main puja is at night, around midnight. Break the fast the next morning.",
   [("Om Namah Shivaya", "shiva-panchakshari"),
    ("Lingashtakam", None)])
_g("holika_dahan",
   ["Join the community bonfire and walk around it.",
    "Offer new wheat or grain and coconut to the fire.",
    "Burn only dry wood and cow-dung cakes; no tyres or plastic."],
   "After sunset, outside the Bhadra time.",
   [("Om Namo Narayanaya", None)])
_g("holi",
   ["Play with natural or safe colours.",
    "Ask before you colour someone; go gently with children, elders and animals.",
    "Share gujiya or a sweet with neighbours.",
    "Bengal and Odisha keep Dol Jatra with Krishna on a swing."],
   "Colours are played in the morning; visits in the evening.",
   [("Madhurashtakam", None)])

# ── Regional and secondary ───────────────────────────────────────────────────
_g("chaitra_navratri",
   ["Set up the kalash, or light a lamp to keep for nine days.",
    "Pray to the Devi each day.",
    "Fast only if your health allows. A simple meal also counts.",
    "The nine days end on Rama Navami."],
   "Kalash is set in the morning on the first day.",
   [("Sarva Mangala Mangalye", "durga-sarvamangala"),
    ("Durga Saptashati (reading)", "durga-saptashati")])
_g("mahavir_jayanti",
   ["Visit a Jain temple, or watch the procession.",
    "Do one kind act for people or animals.",
    "Many eat simple food without onion and garlic today."],
   "Morning.",
   [("Navkar Mantra", None)])
_g("panguni_uthiram",
   ["Visit a Murugan temple for the wedding festival.",
    "Offer flowers and fruit.",
    "It also marks the weddings of Shiva and Parvati, and Rama and Sita."],
   "Morning puja.",
   [("Om Saravanabhavaya Namah", "skanda-shadakshari")])
_g("karadaiyan_nombu",
   ["Make karadai (sweet adai) with a little butter as the offering.",
    "Tie the yellow thread at the time of the Sun's entry into Meena.",
    "Remember Savitri and pray for the family's well-being."],
   "The thread is tied at the exact Sankranti moment; check the time.",
   [("Sarva Mangala Mangalye", "durga-sarvamangala")])
_g("shankara_jayanti",
   ["Read a short work of Adi Shankara.",
    "Visit a Shankara Math or temple if near."],
   "Any time; morning is common.",
   [("Bhaja Govindam", None),
    ("Gurur Brahma", "guru-vandana")])
_g("sita_navami",
   ["Do a simple puja to Sita and Rama.",
    "Read a little from the Sundara Kanda.",
    "Married women often pray for the family's well-being."],
   "Around midday.",
   [("Sri Rama Jaya Rama", "rama-taraka")])
_g("nirjala_ekadashi",
   ["The custom is to go without water and food from sunrise to the next sunrise.",
    "If that is hard, a water and fruit fast is a common, accepted choice.",
    "Give water or a pot of water to others in the heat."],
   "Break the fast the next morning after sunrise. Fast only if your health allows.",
   [("Om Namo Bhagavate Vasudevaya", "vishnu-dvadashakshari"),
    ("Vishnu Sahasranama", "vishnu-sahasranama")])
_g("shani_jayanti",
   ["Light a sesame oil lamp at a Shani or Hanuman temple.",
    "Help someone who works hard for little: a meal, warm clothes, black gram.",
    "No costly rituals are needed."],
   "Evening is common.",
   [("Om Sham Shanaishcharaya Namah", "saturn-nama"),
    ("Shani verse of the Navagraha Stotra", "saturn-stotra")])
_g("devshayani_ekadashi",
   ["Keep the Ekadashi fast if your health allows; skip rice at least.",
    "Pray to Vishnu; in Maharashtra this is Ashadhi Ekadashi for Vitthal.",
    "Some take a small vow for Chaturmas, like giving up one food."],
   "Break the fast the next morning.",
   [("Om Namo Bhagavate Vasudevaya", "vishnu-dvadashakshari"),
    ("Vishnu Sahasranama", "vishnu-sahasranama")])
_g("aadi_perukku",
   ["Offer flowers, turmeric and a lamp at a river, or to a pot of water at home.",
    "Cook mixed rice dishes and share them.",
    "Married women often change the yellow thread."],
   "Morning or midday.",
   [("Lalitha Sahasranama", None)])
_g("aadi_pooram",
   ["Visit an Andal or Amman temple.",
    "Offer glass bangles to the Devi; they are later given to women.",
    "Recite or listen to a few verses of the Tiruppavai."],
   "Morning puja.",
   [("Tiruppavai", None)])
_g("hariyali_teej",
   ["Wear green, put on mehendi, and sing Teej songs.",
    "Pray to Parvati and Shiva.",
    "Fast only if your health allows."],
   "Daytime; puja in the evening is common.",
   [("Sarva Mangala Mangalye", "durga-sarvamangala")])
_g("putrada_ekadashi",
   ["Keep the Ekadashi fast if your health allows; skip rice at least.",
    "Pray to Vishnu for the children of the family."],
   "Break the fast the next morning.",
   [("Om Namo Bhagavate Vasudevaya", "vishnu-dvadashakshari")])
_g("avani_avittam",
   ["Those who wear the sacred thread change it with a priest or elder.",
    "Bathe early and offer a short prayer to the rishis.",
    "Gayatri japa is done the next morning."],
   "Morning. The day differs by Veda (Rig, Yajur, Sama).",
   [("Gayatri mantra", "gayatri")])
_g("kajari_teej",
   ["Women sing Kajari songs and pray to Parvati.",
    "Many pray at a neem tree in the evening.",
    "Fast only if your health allows."],
   "The fast ends at moonrise in many homes.",
   [("Sarva Mangala Mangalye", "durga-sarvamangala")])
_g("hartalika_teej",
   ["Pray to Parvati and Shiva with a clay or sand image.",
    "Hear the Hartalika katha.",
    "Fast only if your health allows. A simple meal also counts.",
    "In Karnataka this is Gowri Habba: give bagina (gift baskets) to married women."],
   "Morning or evening puja. Ganesha comes the next day.",
   [("Sarva Mangala Mangalye", "durga-sarvamangala"),
    ("Gauri Ashtottara Shatanamavali", None)])
_g("rishi_panchami",
   ["Remember the seven rishis: Kashyapa, Atri, Bharadwaja, Vishvamitra, "
    "Gautama, Jamadagni and Vasishtha.",
    "Many women keep a light fast, if health allows."],
   "Morning puja.",
   [("Gurur Brahma", "guru-vandana")])
_g("anant_chaturdashi",
   ["Ganesh idols kept for ten days are immersed today.",
    "Some tie an Anant thread with 14 knots and pray to Vishnu.",
    "Immerse in a tank or a bucket at home where you can."],
   "Immersion in the afternoon or evening.",
   [("Om Gam Ganapataye Namah", "ganesha-nama"),
    ("Vishnu Sahasranama", "vishnu-sahasranama")])
_g("pitru_paksha_begins",
   ["Note the tithi on which each ancestor passed; that is their day this fortnight.",
    "Offer tarpanam or a simple meal in their name, as your family does.",
    "Feed someone in need, a cow or crows."],
   "Rites are done in the late morning or midday.",
   [("Om Namo Bhagavate Vasudevaya", "vishnu-dvadashakshari")])
_g("vishwakarma_puja",
   ["Clean your tools, machines and workplace.",
    "Do a short puja and rest the tools for the day.",
    "In Bengal and Bihar, many fly kites."],
   "Morning.",
   [("Om Vishwakarmane Namah", None)])
_g("bathukamma_begins",
   ["Stack seasonal flowers in rings to make a Bathukamma.",
    "Women gather in the evening, sing Bathukamma songs, and dance around it.",
    "Set it afloat in a pond or lake at the end."],
   "Evening. The nine days end with Saddula Bathukamma.",
   [("Sarva Mangala Mangalye", "durga-sarvamangala")])
_g("atla_taddi",
   ["Eat a little before dawn, then fast through the day if health allows.",
    "Offer atlu (dosas) to Gauri and share them with other women.",
    "Break the fast after seeing the moon."],
   "The fast ends at moonrise; check the time for your city.",
   [("Sarva Mangala Mangalye", "durga-sarvamangala")])
_g("ahoi_ashtami",
   ["Draw Ahoi Mata on the wall or use a picture.",
    "Hear the Ahoi katha in the evening.",
    "Fast only if your health allows."],
   "The fast ends on seeing the stars, or the moon in some homes.",
   [])
_g("nagula_chavithi",
   ["Pray at an anthill (putta) or a snake image.",
    "Offer a little milk, flowers and chalividi to the anthill only.",
    "Never give milk to a live snake or disturb one."],
   "Morning.",
   [("Namostu Sarpebhyah", "sarpa-namostu")])
_g("skanda_sashti",
   ["Pray to Murugan each of the six days.",
    "Many eat one simple meal a day, if health allows.",
    "Watch Soorasamharam at a temple on the sixth day."],
   "Soorasamharam is in the evening of the sixth day.",
   [("Kanda Sashti Kavacham", None),
    ("Om Saravanabhavaya Namah", "skanda-shadakshari")])
_g("devutthana_ekadashi",
   ["Keep the Ekadashi fast if your health allows; skip rice at least.",
    "Pray to Vishnu; many do Tulsi Vivah today or tomorrow.",
    "Chaturmas ends; the wedding season begins."],
   "Break the fast the next morning.",
   [("Om Namo Bhagavate Vasudevaya", "vishnu-dvadashakshari"),
    ("Vishnu Sahasranama", "vishnu-sahasranama")])
_g("guru_nanak_jayanti",
   ["Visit a gurudwara and join the kirtan.",
    "Help at the langar, or share a meal.",
    "Many join the early-morning prabhat pheri."],
   "Gurudwaras hold kirtan from early morning.",
   [("Japji Sahib", None),
    ("Mool Mantar", None)])
_g("dhanurmasa_begins",
   ["Rise early and pray before sunrise through the month.",
    "Recite one Tiruppavai verse a day, or listen to it.",
    "Draw a rangoli (muggu, kolam) at the door each morning."],
   "Early morning, before sunrise.",
   [("Tiruppavai", None),
    ("Vishnu Sahasranama", "vishnu-sahasranama")])
_g("subrahmanya_shashthi",
   ["Visit a Subrahmanya or Murugan temple.",
    "Offer milk and flowers.",
    "In Maharashtra this is Champa Shashthi, for Khandoba."],
   "Morning.",
   [("Om Saravanabhavaya Namah", "skanda-shadakshari"),
    ("Subrahmanya Bhujangam", None)])
_g("arudra_darshan",
   ["Visit a Shiva temple for Nataraja darshan.",
    "Make Thiruvathirai kali and kootu as the offering.",
    "Listen to the Thiruvempavai."],
   "Early morning darshan.",
   [("Om Namah Shivaya", "shiva-panchakshari")])
_g("hanumath_jayanti_south",
   ["Visit a Hanuman temple, or light a lamp at home.",
    "Recite or listen to the Hanuman Chalisa or Sundara Kanda.",
    "Offer a vada or betel leaf garland."],
   "Morning puja.",
   [("Hanuman Chalisa", "hanuman-chalisa"),
    ("Manojavam Marutatulyavegam", "hanuman-manojavam")])
_g("bhogi",
   ["Light a small Bhogi fire at dawn with dry wood and old things.",
    "Burn no plastic, rubber or tyres.",
    "Telugu homes shower children with Bhogi pallu (berries)."],
   "At dawn; oil bath after the fire.",
   [("Tiruppavai", None)])
_g("lohri",
   ["Light the bonfire with family and neighbours in the evening.",
    "Offer til, gur, peanuts and popcorn to the fire.",
    "Sing Lohri songs; it is special for newlyweds and new babies."],
   "After sunset.",
   [])
_g("mattu_pongal",
   ["Bathe cattle, paint their horns and garland them.",
    "Offer them pongal and thank them.",
    "Telugu homes keep Kanuma with a family meal."],
   "Morning to midday.",
   [])
_g("kaanum_pongal",
   ["Visit family and friends, or have a picnic.",
    "Sisters put out rice for birds and pray for their brothers (Kanu pidi)."],
   "Morning for Kanu pidi; the rest of the day is for visits.",
   [])
_g("mauni_amavasya",
   ["Keep silence for some hours, or as long as is easy.",
    "Take a bath, in a river if you can.",
    "Remember ancestors and give food in their name."],
   "Early morning bath.",
   [("Silent japa of any name you hold dear", None)])
_g("bhishma_ashtami",
   ["Offer water (tarpanam) to Bhishma; anyone may do it.",
    "Recite or listen to the Vishnu Sahasranama, which Bhishma taught."],
   "Around midday.",
   [("Vishnu Sahasranama", "vishnu-sahasranama")])
_g("masi_magam",
   ["Take a holy dip at the sea, a river or a temple tank.",
    "Visit the temple; deities are carried to the water.",
    "In Kumbakonam the Mahamaham tank draws big crowds."],
   "Morning.",
   [("Om Namah Shivaya", "shiva-panchakshari")])

# ── Monthly vrat days ────────────────────────────────────────────────────────
_g("ekadashi",
   ["Keep a fast or skip grains and rice, if your health allows.",
    "Pray to Vishnu, morning or evening.",
    "A simple meal also counts."],
   "Break the fast the next morning, after sunrise.",
   [("Om Namo Bhagavate Vasudevaya", "vishnu-dvadashakshari"),
    ("Vishnu Sahasranama", "vishnu-sahasranama")],
   table=VRAT_GUIDANCE)
_g("purnima",
   ["Light a lamp and offer a prayer in the evening.",
    "Many families do the Satyanarayana puja on a full moon.",
    "Give food to someone in need."],
   "Evening, after moonrise.",
   [("Om Chandraya Namah", "moon-nama"),
    ("Lalitha Sahasranama", None)],
   table=VRAT_GUIDANCE)
_g("amavasya",
   ["Remember your ancestors; offer water or food in their name, as your family does.",
    "Light a lamp in the evening.",
    "Many avoid starting new work today. That is a custom, not a rule."],
   "Ancestor offerings are done before sunset.",
   [("Om Namo Bhagavate Vasudevaya", "vishnu-dvadashakshari")],
   table=VRAT_GUIDANCE)
_g("pradosham",
   ["Pray to Shiva at dusk, at home or a temple.",
    "Offer water, bilva leaves or a lamp.",
    "Some fast until the evening puja, if health allows."],
   "Pradosha time is about 1.5 hours either side of sunset.",
   [("Om Namah Shivaya", "shiva-panchakshari"),
    ("Lingashtakam", None)],
   table=VRAT_GUIDANCE)


def _resolved(entry: dict | None) -> dict:
    if entry is None:
        return {"todo": [], "how": None, "mantras": []}
    return {
        "todo": list(entry["todo"]),
        "how": entry["how"],
        "mantras": [{"name": name, "corpus_id": corpus_id}
                    for name, corpus_id in entry["mantras"]],
    }


def for_festival(slug: str) -> dict:
    """``{"todo", "how", "mantras"}`` for a festival slug; empty if unknown."""
    return _resolved(FESTIVAL_GUIDANCE.get(slug))


def for_vrat(kind: str) -> dict:
    """The same shape for a vrat kind (ekadashi, purnima, amavasya, pradosham)."""
    return _resolved(VRAT_GUIDANCE.get(kind))
