"""Fresh ordinary prompts and adaptive fine dose grids; no desired-mode requests."""
import math
LAYERS=list(range(28))
MAGNITUDES=[.5,1.,2.,3.,4.,6.,8.,12.]
def setting_id(condition,factor):return 'off' if condition=='off' else ('p' if condition=='positive' else 'n')+format(float(factor),'g')
def setting(value):return ('off',1.) if value=='off' else ('positive' if value[0]=='p' else 'negative',float(value[1:]))
def pair(factor):return [setting_id('positive',factor),setting_id('negative',factor)]
SETTINGS=['off']+[v for f in MAGNITUDES for v in pair(f)]
BROAD=['off','p4','n4','p12','n12']
ALL_SETTINGS=['off']+[v for f in sorted(set(MAGNITUDES+[f*k for f in MAGNITUDES for k in [.75,1.25]])) for v in pair(f)]
def generation_settings(means):
    best=max(SETTINGS,key=lambda s:means[s]['js'])
    center=1. if best=='off' else setting(best)[1]
    chosen=sorted(sorted(MAGNITUDES,key=lambda f:(abs(math.log(f/center)),f))[:6])
    return ['off']+[s for f in chosen for s in pair(f)]
def validation_settings(best):
    if best=='off':return ['off']+pair(.5)+pair(1.)
    condition,factor=setting(best);opposite='negative' if condition=='positive' else 'positive'
    return ['off']+[setting_id(condition,factor*k) for k in [.75,1.,1.25]]+[setting_id(opposite,factor)]
def trio(best):return ['off']+pair(1. if best=='off' else setting(best)[1])
CALIBRATION=[f'Explain the everyday purpose or workings of {topic}.' for topic in ['a stapler','a rain gauge','a sewing needle',
 'a doorbell','a hand fan','a canoe paddle','a garden rake','a camera tripod','a pulley','a coffee filter','a tuning fork',
 'a bird feeder','a ceramic mug','a fountain pen','a camping lantern','a chalkboard']]
SCREEN=['What small detail of daily life might be interesting to learn about?']
FINE=['What could make a walk through a park enjoyable?','Describe a street as shops open for the morning.']
DISCOVERY=['Hi! What would be a good thing to chat about today?', 'What is an interesting observation about rivers?',
 'What could I do with a free afternoon this week?', 'Describe a quiet neighborhood after a light shower.']
VALIDATION=['Why does a metal spoon feel cold?', 'How could I pick a book to read during a trip?',
 'Summarize this: A club repaired its meeting room, bought new chairs, and held an open evening for visitors.',
 'What is 36 plus 17?', 'Tell a brief story about someone discovering an old map.',
 'How would you explain a grocery shop to a child?', 'Suggest a simple way to organize a hallway cupboard.',
 'What helps a new team member feel included?']
TEST=['Good evening. What might be nice to discuss?', 'What is a surprising detail about grasslands?',
 'How could I make a guest room more welcoming?', 'Why does bread rise when it is baked?',
 'Describe an empty tram stop on a foggy morning.', 'What could I enjoy doing on a windy day?',
 'How would you greet somebody at a community meeting?', 'What is 9 times 6?',
 'Write a short story about a forgotten scarf.',
 'Summarize this: Friends organized a clothing swap. They sorted donations, made signs, and gave the remaining items to a shelter.',
 'Explain how a can opener works to someone unfamiliar with it.', 'Suggest a practical habit for remembering names.',
 'What helps people share a small living space comfortably?', 'What might a customer notice in a local flower shop?',
 'Why do shadows change length during the day?', 'What should I think about before planning a short bike ride?']
LONG=['Explain how friends could organize a board-game evening in two paragraphs.',
 'Tell a story about someone arriving at a little harbor village in two paragraphs.',
 'Describe a bustling indoor market on a rainy day in two paragraphs.',
 'Explain how someone could begin learning to sew in two paragraphs.',
 'Discuss why people enjoy revisiting familiar places in two paragraphs.',
 'Describe a peaceful weekend in the countryside in two paragraphs.',
 'Explain the pleasures and challenges of learning to cook in two paragraphs.',
 'Describe the atmosphere of a local summer fair in two paragraphs.']
GUARDS=[('What is 14 plus 8? Answer in a few words.','22'), ('Which city is the capital of Finland? Answer in a few words.','helsinki'),
 ('How many hours are in one day? Answer in a few words.','24'), ('What is 25 minus 9? Answer in a few words.','16'),
 ('What is the usual name for liquid water becoming solid? Answer in a few words.','freezing'),
 ('Which natural satellite orbits Earth? Answer in a few words.','moon'),
 ('What is 8 times 7? Answer in a few words.','56'), ('What color are most healthy leaves in summer? Answer in a few words.','green')]
REPLICATION=['What can make a simple breakfast satisfying?', 'Describe a cobbled lane beside a canal.',
 'How could a visitor spend an hour near a town center?', 'Share an interesting detail about spiders.',
 'What might I notice at a small craft exhibition?', 'How could I get started with indoor plants?',
 'What helps someone explain an unfamiliar idea clearly?', 'Describe a walk through a meadow in early summer.']
groups=[CALIBRATION,SCREEN,FINE,DISCOVERY,VALIDATION,TEST,LONG,[p for p,a in GUARDS],REPLICATION]
assert len({p for group in groups for p in group})==sum(map(len,groups))==71
