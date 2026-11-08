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
CALIBRATION=[f'In a few sentences, explain {topic}.' for topic in ['a waterfall','a windmill','a marketplace','a notebook',
 'a lighthouse','a snowflake','a thermometer','a telescope','a bookshelf','a ferry','a beehive','a recipe','a fountain','a canyon','a workshop','a seedling']]
SCREEN=['What is an everyday thing that is worth understanding better?']
FINE=['What could make an ordinary afternoon enjoyable?','Describe a village as the evening begins.']
DISCOVERY=['Hello there. What has been on your mind?','What is an interesting thing about mountains?',
 'I have a little spare time today. Any suggestions?','Describe a neighborhood on a cool autumn evening.']
VALIDATION=['How does a refrigerator keep food cool?','What could I consider when choosing a weekend activity?',
 'Summarize this: Neighbors repaired a playground. They painted benches, planted shrubs, and arranged a celebration.',
 'What is 19 plus 14?','Tell a short story about someone discovering a forgotten photograph.',
 'How would you explain a post office to a young child?','Suggest a practical way to organize a kitchen drawer.',
 'What helps people feel welcome in a conversation?']
TEST=['Hi there. What would you like to share today?','What is an interesting fact about deserts?',
 'How might I make a balcony a pleasant place to sit?','Why does a rainbow appear after rain?',
 'Describe an empty bus station just before dawn.','What could someone enjoy doing on a snowy afternoon?',
 'How would you introduce yourself to a new person?','What is 8 times 9?',
 'Write a short story about a misplaced key.','Summarize this: A storm postponed a concert. The performers met at a cafe, rehearsed quietly, and chose a new date.',
 'Explain how a clock works to a beginner.','Suggest a simple habit that helps with remembering things.',
 'What qualities make a person a good neighbor?','What might someone see in a small antique shop?',
 'How do caterpillars become butterflies?','I am arranging a small day trip. What should I think about first?']
LONG=['Explain how friends could set up a reading group in two paragraphs.',
 'Tell a story about a traveler reaching an unfamiliar island in two paragraphs.',
 'Describe a lively train station in two paragraphs.','Explain how a beginner might learn photography in two paragraphs.',
 'Discuss why people enjoy exploring old towns in two paragraphs.','Describe a quiet winter holiday in two paragraphs.',
 'Explain the value of learning a musical instrument in two paragraphs.','Describe a local food market in two paragraphs.']
GUARDS=[('What is 11 plus 7? Please answer briefly.','18'),('What is the capital of Spain? Please answer briefly.','madrid'),
 ('How many days are in a week? Please answer briefly.','7'),('What is 13 minus 4? Please answer briefly.','9'),
 ('What do we call water falling from clouds? Please answer briefly.','rain'),('Which star is closest to Earth? Please answer briefly.','sun'),
 ('What is 5 times 6? Please answer briefly.','30'),('What color is a clear daytime sky usually? Please answer briefly.','blue')]
REPLICATION=['What do people appreciate about a good meal?','Describe a stone courtyard.',
 'What could someone do during a morning in an unfamiliar city?','Share an interesting fact about insects.',
 'What might a visitor notice in an old railway museum?','How can I get started with gardening?',
 'What makes directions easy to follow?','Describe a stroll through an orchard.']
groups=[CALIBRATION,SCREEN,FINE,DISCOVERY,VALIDATION,TEST,LONG,[p for p,a in GUARDS],REPLICATION]
assert len({p for group in groups for p in group})==sum(map(len,groups))==71
