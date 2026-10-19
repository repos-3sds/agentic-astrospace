"""Rebuild astrospace/core/subhashita/subhashitas.json.

The Sanskrit comes from rekey/transcriptions.tsv: each verse keyed by hand
from a scan of a print edition published before 1931 (the editions are in
astrospace/core/subhashita/editions.json), in that print's own spelling.
rekey/normalise.py turns the print spelling into the corpus spelling
without changing a word. The English below and meanings.json are written
for this app. No network is needed.

    python scripts/subhashita/build_corpus.py astrospace/core/subhashita/subhashitas.json
"""
import json, re, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'rekey'))
from normalise import normalise
OUT = sys.argv[1]
EDITIONS = json.load(open(os.path.join(HERE, '..', '..', 'astrospace', 'core', 'subhashita', 'editions.json'), encoding='utf-8'))

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
'16.2': "A good and godly nature shows in non-violence, truth, no anger, letting go, calm, no backbiting, kindness to all, no greed, gentleness, modesty and steadiness.",
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
'1.16': "Take nectar even from poison, gold even from dirt, the finest learning even from a lowly teacher, and a jewel of a wife even from a humble family.",
'2.5': "Steer clear of a friend who undoes your work behind your back and speaks sweetly to your face: a pot of poison with milk on top.",
'2.7': "What you have planned in your mind, don't announce in words. Guard it quietly with careful thought, and then put it into action.",
'2.9': "Not every mountain holds rubies, not every elephant a pearl, not every forest sandalwood. Good people, too, are not found everywhere.",
'2.13': "Don't let a day go to waste. Learn a verse, half a verse, a quarter, even a single letter, and fill it with giving, study and good work.",
'3.4': "Between a wicked person and a snake, the snake is better: a snake bites only when its time comes, the wicked one at every step.",
'3.6': "At the end of an age even the oceans break their shores. Good people never break their bounds, not even then.",
'3.8': "Beauty, youth and a great family name don't shine without learning, like palash flowers: bright, but without fragrance.",
'3.11': "Effort keeps poverty away, prayer keeps wrongdoing away, silence keeps quarrels away, and alertness keeps fear away.",
'3.13': "What is too heavy for the capable? What is too far for the determined? What land is foreign to the learned? Who is not a friend to the kind-spoken?",
'3.14': "One flowering, fragrant tree perfumes a whole forest. In the same way, one worthy child brings fragrance to a whole family.",
'4.3': "As a fish, a tortoise and a bird care for their young by sight, by thought and by touch, the company of good people cares for us.",
'4.5': "Learning is like the wish-fulfilling cow: it gives even out of season. Far from home it looks after you like a mother. It is hidden wealth.",
'4.6': "One child with good qualities is worth more than a hundred without. One moon dispels the dark; thousands of stars do not.",
'4.18': "Ask yourself again and again: What time is it? Who are my friends? Where am I? What comes in and what goes out? Whom do I belong to, and what is my strength?",
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
'10.16': "Intelligence is strength; without it, where is strength? In the forest, a lion drunk with pride was brought down by a jackal.",
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
('Bhagavata Purana', '1.2.6', "The highest dharma for anyone is the one that awakens selfless, unbroken devotion to the Divine. Through it, the self becomes truly at peace."),
('Bhagavata Purana', '1.8.25', "Let hardships come again and again, O Teacher of the world, if in each of them I get to see You: the sight that ends the round of rebirth."),
('Bhagavata Purana', '4.31.14', "Water a tree's root and its trunk and branches are all nourished; feed the life-breath and every sense is fed. So, worshipping the Divine honours all."),
('Bhagavata Purana', '7.5.23', "Devotion has nine forms: hearing of Vishnu, singing of Him, remembering Him, serving His feet, worship, bowing down, service, friendship, and offering your whole self."),
('Bhagavata Purana', '9.21.12', "I don't ask God for the highest state, its powers, or release from rebirth. I would take on the pain of all beings, so that they may be free of sorrow."),
('Bhagavata Purana', '10.22.35', "This is what makes a life worthwhile: always doing good for others with your life, your means, your understanding and your words."),
('Bhagavata Purana', '11.2.36', "Whatever you do, with body, speech, mind, senses, intellect or by your own nature, offer all of it to the Divine, saying: this is for Narayana."),
('Bhagavata Purana', '12.13.23', "I bow to Hari, the Supreme, whose name, sung aloud, washes away every wrong, and to whom a simple bow brings sorrow to rest."),
('Vishnu Purana', '1.17.90', "Don't take delight in the empty turns of this world, I tell you plainly. Look on all as equal everywhere: evenness of mind is itself the worship of God."),
('Vishnu Purana', '1.19.41', "True action is action that doesn't bind; true knowledge is knowledge that sets you free. Other action is only toil; other knowledge only a craft."),
('Garuda Purana', '1.108.12', "One who keeps company with the noble, good conversation with the wise and friendship with the unselfish never comes to grief."),
('Garuda Purana', '1.109.4', "The wise move one foot while keeping the other planted. Don't leave your old place before you have looked over the new one."),
('Garuda Purana', '1.110.16', "Even when harassed, a person of steady courage can't be stripped of their goodness. Turn a flame upside down and it still burns upward."),
('Garuda Purana', '1.110.30', "No one here knows everything, and no one is a complete fool. Whatever a person knows, humble, middling or high, in that they are learned."),
('Garuda Purana', '1.111.24', "The steady don't despair when hardship comes. Doesn't the moon rise again after Rahu swallows it?"),
('Garuda Purana', '1.113.9', "For a craving mind, faults arise even in the forest. At home, mastering the senses is itself austerity. For one free of craving, doing honest work, home is a hermitage."),
('Garuda Purana', '1.113.13', "Learning adorns the scholar, a good ruler adorns the land, the moon adorns the sky, but good character adorns everyone."),
('Garuda Purana', '1.113.34', "True learning never runs low; it grows as you give it away, like water in a well that keeps filling as it is drawn."),
('Garuda Purana', '1.113.42', "Not puffed up by honour, not angered by insult, and never harsh in speech even when angry: these are the marks of a good person."),
('Markandeya Purana', '58.71', "Bear ill will toward no being, and offer friendship. Steer clear of untrue words and of hurtful, excessive talk."),
('Markandeya Purana', '85.23', "To the Goddess who dwells in every being as peace: salutations to Her, salutations to Her, salutations to Her, again and again."),
('Markandeya Purana', '91.9', "O auspicious one, the blessing within every blessing, who brings every aim to fulfilment, our refuge, three-eyed Gauri, Narayani: salutations to you."),
]

REKEY = {}
for line in open(os.path.join(HERE, 'rekey', 'transcriptions.tsv'), encoding='utf-8'):
    if line.startswith('#') or not line.strip(): continue
    vid, edition, leaf, page, text, note = line.rstrip('\n').split('\t')
    assert edition in EDITIONS, (vid, edition)
    REKEY[vid] = (normalise(text.replace('\\n', '\n')), {
        'edition': edition,
        'scan_page_url': f"https://archive.org/details/{EDITIONS[edition]['archive_id']}/page/n{int(leaf)}/mode/1up",
        'page': page or None,
        'note': note or None,
    })

def rekeyed(vid):
    assert vid in REKEY, 'no transcription for ' + vid
    return REKEY[vid]

entries = {'g': [], 'c': [], 'p': []}
for ref, en in GITA.items():
    vid = 'gita-' + ref.replace('.', '-'); sa, prov = rekeyed(vid)
    entries['g'].append({'id': vid, 'source': 'Bhagavad Gita', 'ref': ref, 'sanskrit': sa, 'english': en, 'provenance': prov})
for ref, en in CHANAKYA.items():
    vid = 'chanakya-' + ref.replace('.', '-'); sa, prov = rekeyed(vid)
    entries['c'].append({'id': vid, 'source': 'Chanakya Niti', 'ref': ref, 'sanskrit': sa, 'english': en, 'provenance': prov})
IDP = {'Bhagavata Purana': 'bhagavata', 'Vishnu Purana': 'vishnu', 'Garuda Purana': 'garuda', 'Markandeya Purana': 'markandeya'}
for src, ref, en in PURANA:
    vid = IDP[src] + '-' + ref.replace('.', '-'); sa, prov = rekeyed(vid)
    entries['p'].append({'id': vid, 'source': src, 'ref': ref, 'sanskrit': sa, 'english': en, 'provenance': prov})

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
# The one-line plain meaning shown under each verse (Hawk, 2026-10-18: a
# verse on its own read as half a sentence). Kept beside this script.
MEANINGS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'meanings.json'), encoding='utf-8'))
assert set(MEANINGS) == {e['id'] for e in res}, 'every verse needs a meaning'
assert set(REKEY) == {e['id'] for e in res}, 'every verse needs a transcription'
res = [{**{k: e[k] for k in ('id', 'source', 'ref', 'sanskrit', 'english')}, 'meaning': MEANINGS[e['id']], 'provenance': e['provenance']} for e in res]
json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
