import json, re, sys, os
D = str.maketrans('०१२३४५६७८९', '0123456789')
BASE = sys.argv[1]  # scratch dl dir
OUT = sys.argv[2]
RAW = 'https://raw.githubusercontent.com/sanskrit/raw_etexts/master/'
GITA_URL = 'https://raw.githubusercontent.com/vedicscriptures/bhagavad-gita-data/main/slok/bhagavadgita_chapter_{c}_slok_{v}.json'
CN_PATH = 'mixed/ebhAratI-sampat/subhAShitasangrahaH/subhAShitasangrahasambaddhapustakAni/chANakyaH/chANakyanItidarpaNam.md'
PUR = 'mixed/gretil_devanAgarI/1_sanskr/3_purana/'

GITA = {
'2.14': "Heat and cold, pleasure and pain come from the senses meeting the world. They come and they go; none of them lasts. Bear them with patience.",
'2.40': "On this path no effort is ever lost, and nothing you do here works against you. Even a little of it protects you from great fear.",
'2.47': "Your right is to the work alone, never to its fruits. Don't let results be your reason for acting, and don't let that turn you toward doing nothing.",
'2.48': "Rooted in yourself, do your work and let go of clinging. Stay the same in success and failure. That evenness is what yoga means.",
'2.50': "One whose understanding is steady leaves behind both good and bad deeds, even here. So give yourself to yoga: yoga is skill in action.",
'2.55': "When a person lets go of every craving in the mind and is content in the Self, by the Self, they are called steady in wisdom.",
'2.56': "Not shaken by sorrow, not hungry for pleasure, free of attachment, fear and anger: such a person is called a sage of steady mind.",
'2.58': "Like a tortoise drawing in its limbs, one who can draw the senses back from what pulls at them has wisdom that stands firm.",
'2.62': "Keep dwelling on things and attachment to them grows. Attachment gives birth to desire, and desire gives birth to anger.",
'2.63': "Anger brings confusion, confusion scatters memory, a scattered memory ruins understanding, and when understanding is lost, a person is lost.",
'2.65': "In that inner calm, every sorrow falls away. For one whose heart is clear, understanding soon becomes steady.",
'2.66': "Without inner discipline there is no clear understanding and no deep reflection. Without reflection there is no peace. Without peace, where is happiness?",
'2.70': "Rivers keep pouring into the ocean, yet it stays full and still. One whom desires enter like that finds peace, not one who chases desires.",
'2.71': "One who sets aside every craving and moves through life free of longing, without 'mine' and without ego, comes to peace.",
'3.8': "Do the work that is yours to do; action is better than inaction. Without action you could not even keep your body going.",
'3.19': "So, without attachment, keep doing the work that needs doing. By acting without attachment, a person reaches the highest.",
'3.21': "Whatever the best among us do, others follow. Whatever standard they set, the world goes along with it.",
'3.37': "It is desire, it is anger, born of restless passion: never satisfied and the root of much wrong. Know this to be the enemy here.",
'4.7': "Whenever goodness fades and wrongdoing rises, I bring Myself forth into the world.",
'4.11': "However people approach Me, I receive them in that same way. Everywhere, people are walking My path.",
'4.24': "The offering is the Divine, the oblation is the Divine, poured by the Divine into the Divine fire. One who sees the Divine in every act reaches the Divine.",
'4.34': "Learn it through humble respect, honest questions and service. The wise, who have seen the truth, will teach you.",
'4.36': "Even if you were the worst wrongdoer of all, the raft of knowledge alone would carry you across every wrong.",
'4.38': "Nothing in this world purifies like knowledge. One made whole through yoga finds it within, in time.",
'4.39': "One who has faith, gives themselves to it and masters the senses gains knowledge, and having gained it, soon finds the highest peace.",
'5.10': "One who acts without clinging and offers every act to the Divine is untouched by wrong, as a lotus leaf is untouched by water.",
'5.29': "Knowing Me as the one who receives every offering and discipline, the great Lord of all worlds and the friend of every being, a person finds peace.",
'6.5': "Lift yourself up by your own effort; don't let yourself sink. You alone are your own friend, and you alone can be your own enemy.",
'6.6': "For one who has mastered themselves, the self is a friend. For one who has not, their own self behaves like an enemy.",
'6.9': "One who looks with the same even mind on well-wishers, friends, foes, strangers, rivals, relatives, the good and the wrongdoers stands out.",
'6.17': "For one who is balanced in eating and in play, balanced in effort at work, balanced in sleep and in waking, yoga becomes the end of sorrow.",
'6.19': "Like a lamp in a windless place that does not flicker: that is the picture of a disciplined mind absorbed in meditation.",
'6.26': "Wherever the restless, unsteady mind wanders off to, gently bring it back from there and settle it within the Self.",
'6.30': "One who sees Me everywhere and sees everything in Me: I am never lost to them, and they are never lost to Me.",
'6.32': "One who sees every being as they see themselves, feeling others' joy and sorrow as their own, is counted the highest yogi.",
'6.35': "Yes, the mind is restless and hard to hold. But with steady practice and letting go, it can be held.",
'6.40': "No one who does good ever comes to a bad end, dear one, neither in this world nor the next.",
'9.22': "Those who think of Me alone and worship Me, always devoted: I bring them what they lack and keep safe what they have.",
'9.26': "A leaf, a flower, a fruit, a little water: whatever is offered to Me with love by a sincere heart, I gladly accept.",
'9.29': "I am the same to all beings; no one is hateful or dear to Me. But those who worship Me with love are in Me, and I am in them.",
'9.31': "Soon they become good at heart and reach lasting peace. Know this for certain: one who loves Me is never lost.",
'10.20': "I am the Self, seated in the heart of every being. I am their beginning, their middle and their end.",
'12.14': "Always content, self-controlled, firm in resolve, with mind and understanding given to Me: that devotee is dear to Me.",
'12.15': "One who troubles no one and is not troubled by anyone, free from elation, envy, fear and anxiety: that person is dear to Me.",
'12.19': "Even in blame and praise, quiet, content with whatever comes, not tied to one place, steady in mind and full of devotion: that person is dear to Me.",
'16.2': "Non-violence, truth, freedom from anger, letting go, calm, no backbiting, kindness to all beings, no greed, gentleness, modesty and steadiness.",
'16.21': "Desire, anger and greed: these three are the gateways to one's own ruin. So let all three go.",
'17.3': "Everyone's faith takes the shape of their nature. A person is made of their faith: as their faith is, so are they.",
'17.15': "Words that hurt no one and are true, kind and helpful, along with regular study: this is called the discipline of speech.",
'17.16': "A clear and calm mind, gentleness, silence, self-control and a pure heart: this is called the discipline of the mind.",
'17.20': "A gift given simply because giving is right, to one who cannot repay, at the right place and time, to a worthy person: that is pure giving.",
'18.46': "The One from whom all beings arise and who pervades all this: by honouring Him through your own work, you find fulfilment.",
'18.48': "Don't abandon the work that is natural to you, even if it has flaws. Every undertaking carries some flaw, as fire comes wrapped in smoke.",
'18.63': "I have shared with you wisdom deeper than any secret. Reflect on it fully, then do as you choose.",
'18.66': "Let go of every other duty and take refuge in Me alone. I will free you from all wrongs. Do not grieve.",
}

CHANAKYA = {
'1.16': "Take nectar even from poison, gold even from dirt, good conduct even from a rival, and wise words even from a child.",
'2.5': "Steer clear of a friend who undoes your work behind your back and speaks sweetly to your face: a pot of poison with milk on top.",
'2.7': "What you have planned in your mind, don't announce in words. Guard it quietly with careful thought, and then put it into action.",
'2.9': "Not every mountain holds rubies, not every elephant a pearl, not every forest sandalwood. Good people, too, are not found everywhere.",
'2.13': "Don't let a day go to waste. Learn a verse, half a verse, a quarter, even a single letter, and fill it with giving, study and good work.",
'3.4': "Between a wicked person and a snake, the snake is better: a snake bites only when its time comes, the wicked one at every step.",
'3.6': "At the end of an age even the oceans break their shores. Good people never break their bounds, not even then.",
'3.8': "Beauty, youth and a great family name don't shine without learning, like palash flowers: bright, but without fragrance.",
'3.11': "Effort keeps poverty away, prayer keeps wrongdoing away, silence keeps quarrels away, and alertness keeps fear away.",
'3.13': "What is too heavy for the capable? What is too far for the determined? What land is foreign to the learned? Who is a stranger to the kind-spoken?",
'3.14': "One flowering, fragrant tree perfumes a whole forest. In the same way, one worthy child brings fragrance to a whole family.",
'4.3': "As a fish, a tortoise and a bird care for their young by sight, by thought and by touch, the company of good people cares for us.",
'4.5': "Learning is like the wish-fulfilling cow: it gives even out of season. Far from home it looks after you like a mother. It is hidden wealth.",
'4.6': "One child with good qualities is worth more than a hundred without. One moon dispels the dark; thousands of stars do not.",
'4.18': "Ask yourself again and again: What time is it? Who are my friends? Where am I? What comes in and what goes out? Who am I, and what is my strength?",
'5.2': "Gold is tested four ways: rubbing, cutting, heating and beating. A person is tested four ways too: by generosity, conduct, qualities and deeds.",
'5.4': "Born of the same mother, even under the same birth star, people are not alike in character, like the berries and thorns of one bush.",
'5.8': "Learning is kept alive by practice, a family's name by good conduct. A noble person is known by their qualities, and anger shows in the eyes.",
'5.11': "Giving ends poverty, good conduct ends misfortune, wisdom ends ignorance, and steady reflection ends fear.",
'5.19': "By truth the earth is upheld, by truth the sun shines, by truth the wind blows. Everything rests on truth.",
'6.9': "The self does its own deeds and tastes their fruit itself. It wanders through the world on its own, and on its own it is set free.",
'6.16': "Whatever you set out to do, big or small, do it with your whole effort. That is the one lesson to learn from the lion.",
'7.3': "The peace and joy of those filled with the nectar of contentment never come to those who run here and there, greedy for money.",
'8.11': "God is not in wood, nor in stone, nor in clay. God lives in heartfelt devotion, so it is the feeling within that truly matters.",
'8.15': "Virtue adorns beauty, good conduct adorns a family, accomplishment adorns learning, and putting it to good use adorns wealth.",
'9.1': "If you want freedom, my friend, leave sense-cravings like poison, and drink in patience, honesty, kindness, purity and truth like nectar.",
'9.14': "Poverty shines through courage, plain clothes through cleanliness, simple food when served warm, and plain looks through good character.",
'10.1': "Lacking money doesn't make you lacking; such a person may still be truly rich. One who lacks the jewel of learning lacks in everything.",
'10.3': "If you want comfort, give up learning; if you want learning, give up comfort. Where is learning for the comfort-seeker, or comfort for the learner?",
'10.9': "What can books do for someone with no understanding of their own? What can a mirror do for someone without eyes?",
'10.16': "Intelligence is strength; without it, where is strength? In the forest, a proud and reckless lion was brought down by a hare.",
'11.1': "Generosity, kind speech, courage and a sense of what is fitting are not gained by practice. These four are inborn.",
'12.7': "In good company even the unkind grow good, but the good don't turn bad in bad company. Earth takes on a flower's fragrance; flowers never smell of earth.",
'12.8': "Just seeing good people is a blessing; they are living places of pilgrimage. A pilgrimage bears fruit in time, good company at once.",
'12.11': "Truth is my mother, knowledge my father, dharma my brother, compassion my friend, peace my spouse, forgiveness my child. These six are my family.",
'12.22': "Drop by drop, a pot is filled. That is the secret of all learning, of goodness and of wealth.",
'13.2': "Don't grieve over what is past, and don't brood over what is to come. The wise live by the present moment.",
'13.12': "Clinging to sense-pleasures binds; a mind free of them is free. The mind alone is the cause of a person's bondage and freedom.",
'13.15': "As a calf finds its own mother among a thousand cows, the deeds a person has done find their way back to the doer.",
'14.1': "The earth has three jewels: water, food and wise words. Only the foolish call pieces of stone jewels.",
'14.4': "Many together can overcome any foe. Even blades of grass, woven together, hold back the rain of a storm cloud.",
'14.8': "Never be too amazed by anyone's generosity, discipline, courage, knowledge, humility or good judgement. The earth holds many jewels.",
'14.9': "One who lives in your heart is never far, even far away. One who is not in your heart is distant, even standing beside you.",
'15.10': "Scriptures are endless and branches of learning many, but time is short and obstacles are many. Take the essence, as the swan draws milk from water.",
'17.12': "Hands are graced by giving, not bangles; you are cleansed by bathing, not sandal paste; fed by respect, not food; freed by knowledge, not finery.",
}

# (source, ref, file, english)
PURANA = [
('Bhagavata Purana', '1.2.6', 'bhagp/bhagavata-purana_1.md', "The highest dharma for anyone is the one that awakens selfless, unbroken devotion to the Divine. Through it, the self becomes truly at peace."),
('Bhagavata Purana', '1.8.25', 'bhagp/bhagavata-purana_1.md', "Let hardships come again and again, O Teacher of the world, if in each of them I get to see You: the sight that ends the round of rebirth."),
('Bhagavata Purana', '4.31.14', 'bhagp/bhagavata-purana_4.md', "Water a tree's root and its trunk and branches are all nourished; feed the life-breath and every sense is fed. So, worshipping the Divine honours all."),
('Bhagavata Purana', '7.5.23', 'bhagp/bhagavata-purana_7.md', "Hearing of Vishnu, singing of Him, remembering Him, serving His feet, worship, bowing down, service, friendship, and offering your whole self."),
('Bhagavata Purana', '9.21.12', 'bhagp/bhagavata-purana_9.md', "I don't ask God for the highest state, its powers, or release from rebirth. I would take on the pain of all beings, so that they may be free of sorrow."),
('Bhagavata Purana', '10.22.35', 'bhagp/bhagavata-purana_10.md', "This is what makes a life worthwhile: always doing good for others with your life, your means, your understanding and your words."),
('Bhagavata Purana', '11.2.36', 'bhagp/bhagavata-purana_11.md', "Whatever you do, with body, speech, mind, senses, intellect or by your own nature, offer all of it to the Divine, saying: this is for Narayana."),
('Bhagavata Purana', '12.13.23', 'bhagp/bhagavata-purana_12.md', "I bow to Hari, the Supreme, whose name, sung aloud, washes away every wrong, and to whom a simple bow brings sorrow to rest."),
('Vishnu Purana', '1.17.90', 'visnu-purana.md', "Don't take delight in the empty turns of this world, I tell you plainly. Look on all as equal everywhere: evenness of mind is itself the worship of God."),
('Vishnu Purana', '1.19.41', 'visnu-purana.md', "True action is action that doesn't bind; true knowledge is knowledge that sets you free. Other action is only toil; other knowledge only a craft."),
('Garuda Purana', '1.108.12', 'garuda-purana_part_1.md', "One who keeps company with the noble, good conversation with the wise and friendship with the unselfish never comes to grief."),
('Garuda Purana', '1.109.4', 'garuda-purana_part_1.md', "The wise move one foot while keeping the other planted. Don't leave your old place before you have looked over the new one."),
('Garuda Purana', '1.110.16', 'garuda-purana_part_1.md', "Even when harassed, a person of steady courage can't be stripped of their goodness. Turn a flame upside down and it still burns upward."),
('Garuda Purana', '1.110.30', 'garuda-purana_part_1.md', "No one here knows everything, and no one is a complete fool. Whatever a person knows, humble, middling or high, in that they are learned."),
('Garuda Purana', '1.111.24', 'garuda-purana_part_1.md', "The steady don't despair when hardship comes. Doesn't the moon rise again after Rahu swallows it?"),
('Garuda Purana', '1.113.9', 'garuda-purana_part_1.md', "For a craving mind, faults arise even in the forest. At home, mastering the senses is itself austerity. For one free of craving, doing honest work, home is a hermitage."),
('Garuda Purana', '1.113.13', 'garuda-purana_part_1.md', "Learning adorns the scholar, a good ruler adorns the land, the moon adorns the sky, but good character adorns everyone."),
('Garuda Purana', '1.113.34', 'garuda-purana_part_1.md', "True learning never runs low; it grows as you give it away, like water in a well that keeps filling as it is drawn."),
('Garuda Purana', '1.113.42', 'garuda-purana_part_1.md', "Not puffed up by honour, not angered by insult, and never harsh in speech even when angry: these are the marks of a good person."),
('Markandeya Purana', '58.71', 'markandeya-purana_adhyayas_1-93.md', "Bear ill will toward no being, and offer friendship. Steer clear of untrue words and of hurtful, excessive talk."),
('Markandeya Purana', '85.23', 'markandeya-purana_adhyayas_1-93.md', "To the Goddess who dwells in every being as peace: salutations to Her, salutations to Her, salutations to Her, again and again."),
('Markandeya Purana', '91.9', 'markandeya-purana_adhyayas_1-93.md', "O auspicious one, the blessing within every blessing, who brings every aim to fulfilment, our refuge, three-eyed Gauri, Narayani: salutations to you."),
]

def gita(ref):
    c, v = ref.split('.')
    d = json.load(open(f'{BASE}/gita/{ref}.json', encoding='utf-8'))
    assert str(d['chapter']) == c and str(d['verse']) == v, ref
    lines = [l.strip() for l in d['slok'].strip().split('\n') if l.strip()]
    lines = [l for l in lines if not re.search(r'वाच\s*\|?$', l)]
    out = []
    for l in lines:
        l = re.sub(r'\s*\(or [^)]*\)', '', l)
        l = re.sub(r'\s*\|\|[^|]*\|\|\s*$', ' ॥', l)
        l = re.sub(r'\s*\|\s*$', ' ।', l)
        out.append(l)
    return '\n'.join(out), GITA_URL.format(c=c, v=v)

cn_text = None
def chanakya(ref):
    global cn_text
    if cn_text is None:
        lines = [l.strip() for l in open(f'{BASE}/raw_etexts/{CN_PATH}', encoding='utf-8') if l.strip()]
        ch = 0; buf = []; cn_text = {}
        for l in lines:
            m = re.match(r'^\*\*\((\S+)\)', l)
            if m: ch = int(m.group(1).translate(D)); buf = []; continue
            if 'प्रथमोऽध्यायः' in l and ch == 0: ch = 1; continue
            if l.startswith('**') or l.startswith('-') or not ch: continue
            buf.append(l)
            m = re.search(r'॥\s*([०-९]+)\s*॥\s*$', l)
            if m:
                cn_text[f'{ch}.{int(m.group(1).translate(D))}'] = buf; buf = []
    out = []
    for l in cn_text[ref]:
        l = re.sub(r'\s*॥\s*[०-९]+\s*॥\s*$', ' ॥', l)
        # e-text drops the virama of a final -t before the danda (कारयेत। for कारयेत्।); restore it
        l = re.sub(r'त(\s*[।॥])$', r'त्\1', l)
        l = re.sub(r'(\S)([।॥])$', r'\1 \2', l)
        out.append(l)
    return '\n'.join(out), RAW + CN_PATH

def join_gretil(s):
    s = s.replace('-', '')
    vow = {'अ': '', 'आ': 'ा', 'इ': 'ि', 'ई': 'ी', 'उ': 'ु', 'ऊ': 'ू', 'ऋ': 'ृ', 'ए': 'े', 'ऐ': 'ै', 'ओ': 'ो', 'औ': 'ौ'}
    s = re.sub(r'्\s+([अआइईउऊऋएऐओऔ])', lambda m: vow[m.group(1)], s)
    s = re.sub(r'्\s+(?=[क-ह])', '्', s)
    s = re.sub(r'\s+ऽ', 'ऽ', s)
    s = s.replace('दैत्याःसमता', 'दैत्याः समता')
    return re.sub(r'\s+', ' ', s).strip()

def bhp(path, ref):
    parts = [int(x) for x in ref.split('.')]
    halves = []
    for line in open(path, encoding='utf-8'):
        m = re.match(r'^(\S+?)_([०-९।]+)\s+(.*)$', line.strip())
        if not m: continue
        nums = [int(x) for x in m.group(2).translate(D).split('।') if x]
        if nums[:3] == parts and len(nums) == 4 and nums[3] > 0:
            halves.append(join_gretil(m.group(3)))
    assert len(halves) == 2, (ref, halves)
    return f'{halves[0]} ।\n{halves[1]} ॥'

def tagged(path, ref, tag):
    # lines end with "॥ tag_x,y।z ॥"; verse = preceding line(s) since previous tag
    a, b = ref.rsplit('.', 1)
    deva = lambda n: str(n).translate(str.maketrans('0123456789', '०१२३४५६७८९'))
    if tag == 'मर्क्प्':
        label = f'{tag}_{deva(a)}।{deva(b)}'
    else:
        x, y = a.split('.')
        label = f'{tag}_{deva(x)},{deva(y)}।{deva(b)}'
    lines = [l.strip() for l in open(path, encoding='utf-8')]
    for i, l in enumerate(lines):
        if re.search(r'॥\s*' + re.escape(label) + r'\s*॥', l):
            prev = lines[i - 1]
            assert prev.endswith('।'), (ref, prev)
            l1 = join_gretil(prev[:-1]); l2 = join_gretil(re.sub(r'॥.*$', '', l))
            return f'{l1} ।\n{l2} ॥'
    raise SystemExit('not found ' + ref)

entries = {'g': [], 'c': [], 'p': []}
for ref, en in GITA.items():
    sa, url = gita(ref)
    entries['g'].append({'id': 'gita-' + ref.replace('.', '-'), 'source': 'Bhagavad Gita', 'ref': ref, 'sanskrit': sa, 'english': en, 'verified_from': url})
for ref, en in CHANAKYA.items():
    sa, url = chanakya(ref)
    entries['c'].append({'id': 'chanakya-' + ref.replace('.', '-'), 'source': 'Chanakya Niti', 'ref': ref, 'sanskrit': sa, 'english': en, 'verified_from': url})
TAGS = {'Vishnu Purana': 'विप्', 'Garuda Purana': 'गर्प्', 'Markandeya Purana': 'मर्क्प्'}
IDP = {'Bhagavata Purana': 'bhagavata', 'Vishnu Purana': 'vishnu', 'Garuda Purana': 'garuda', 'Markandeya Purana': 'markandeya'}
for src, ref, f, en in PURANA:
    p = f'{BASE}/raw_etexts/{PUR}{f}'
    sa = bhp(p, ref) if src == 'Bhagavata Purana' else tagged(p, ref, TAGS[src])
    entries['p'].append({'id': IDP[src] + '-' + ref.replace('.', '-'), 'source': src, 'ref': ref, 'sanskrit': sa, 'english': en, 'verified_from': RAW + PUR + f})

# spread each family across the array; Puranas internally rotated by source
pur = entries['p']
order = ['Bhagavata Purana', 'Garuda Purana', 'Vishnu Purana', 'Markandeya Purana']
buckets = {s: [e for e in pur if e['source'] == s] for s in order}
pur_mixed = []
while any(buckets.values()):
    for s in ['Bhagavata Purana', 'Garuda Purana', 'Bhagavata Purana', 'Garuda Purana', 'Vishnu Purana', 'Markandeya Purana']:
        if buckets[s]: pur_mixed.append(buckets[s].pop(0))
fam = {'g': entries['g'], 'c': entries['c'], 'p': pur_mixed}
N = sum(len(v) for v in fam.values())
idx = {k: 0 for k in fam}; res = []; last = None
for i in range(N):
    # pick family most behind its ideal share, never repeating the previous family
    best = None
    for k, v in fam.items():
        if idx[k] >= len(v) or k == last: continue
        lag = (i + 1) * len(v) / N - idx[k]
        if best is None or lag > best[0]: best = (lag, k)
    if best is None:
        best = (0, [k for k in fam if idx[k] < len(fam[k])][0])
    k = best[1]; res.append(fam[k][idx[k]]); idx[k] += 1; last = k

# the app wraps (day mod length), so the last entry must not share a source with the first
if res[-1]['source'] == res[0]['source']:
    res[-1], res[-2] = res[-2], res[-1]
# checks
ids = [e['id'] for e in res]; assert len(ids) == len(set(ids))
for e in res:
    assert len(e['english']) <= 180, (e['id'], len(e['english']))
    assert e['sanskrit'].endswith('॥'), e['id']
    assert re.search(r'[a-zA-Z0-9|]', e['sanskrit']) is None, e['id']
adj = sum(1 for a, b in zip(res, res[1:] + res[:1]) if a['source'] == b['source'])
print('total', len(res), 'adjacent-same (incl wrap):', adj)
from collections import Counter; print(Counter(e['source'] for e in res))
json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
