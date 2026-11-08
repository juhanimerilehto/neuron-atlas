"""Distinct ordinary prompts; no requests for the behavioral modes being sought."""
SETTINGS=['off','p1','n1','p4','n4','p12','n12']
LAYERS=list(range(28))
CALIBRATION=[f'Briefly explain {topic}.' for topic in ['a river','a bicycle','a garden','a library','a cloud','a kitchen',
 'a compass','a triangle','a calendar','a musical instrument','a train','a bridge','a tree','a boat','a classroom','a photograph']]
SCREEN=['Tell me something interesting.','What would you recommend for a relaxing weekend?']
DISCOVERY=['Hi. What would you like to talk about?','What is something interesting about the ocean?',
 'I have a free afternoon. What could I do?','Describe a small town on a rainy morning.']
VALIDATION=['How does a bicycle work?','What should I keep in mind when choosing a hobby?',
 'Summarize this: A community opened a reading room. Volunteers donated books, organized shelves, and began weekly events.',
 'What is 17 plus 8?','Tell a short story about a person finding an old map.',
 'How would you describe a library to a child?','Can you suggest a simple way to organize a desk?',
 'What do you think makes a conversation enjoyable?']
TEST=['Hello. How is your day going?','What is something surprising about forests?','How can I make a small room feel comfortable?',
 'Explain why the moon appears to change shape.','Describe a quiet railway platform.',
 'What are some enjoyable things to do on a sunny morning?','Tell me about yourself.',
 'What is 6 times 7?','Write a brief story about a lost letter.',
 'Summarize this: Rain delayed the school picnic. The class moved indoors, shared lunch, and played board games.',
 'How would you explain a compass to a beginner?','Can you suggest a useful habit for learning?',
 'What makes a good friend?','What would someone notice in a seaside bookshop?',
 'How do seeds become plants?','I am planning a small gathering. Where should I start?']
LONG=['Explain how a local community could start a garden in two paragraphs.',
 'Tell a story about a musician arriving in a new city in two paragraphs.',
 'Describe a busy harbor in two paragraphs.','Explain how someone might learn to draw in two paragraphs.',
 'Discuss the appeal of visiting museums in two paragraphs.','Describe a peaceful camping trip in two paragraphs.',
 'Explain the value of keeping a journal in two paragraphs.','Describe a neighborhood festival in two paragraphs.']
GUARDS=[('What is 9 plus 6? Answer briefly.','15'),('What is the capital of Italy? Answer briefly.','rome'),
 ('How many months are in a year? Answer briefly.','12'),('What is 8 minus 3? Answer briefly.','5'),
 ('What is frozen water called? Answer briefly.','ice'),('Which planet do humans live on? Answer briefly.','earth'),
 ('What is 4 times 3? Answer briefly.','12'),('What color is a ripe banana usually? Answer briefly.','yellow')]
REPLICATION=['What do people enjoy about music?','Describe a wooden footbridge.',
 'How would you spend an afternoon in a new town?','Tell me an interesting fact about birds.',
 'What might someone notice in an old theater?','How can I begin learning to cook?',
 'What makes a helpful explanation?','Describe a walk beside a lake.']

def setting(setting):
    if setting=='off':return 'off',1.
    return ('positive' if setting[0]=='p' else 'negative'),float(setting[1:])
def trio(best):
    factor='1' if best=='off' else best[1:]
    return ['off','p'+factor,'n'+factor]

groups=[CALIBRATION,SCREEN,DISCOVERY,VALIDATION,TEST,LONG,[p for p,a in GUARDS],REPLICATION]
assert len({p for group in groups for p in group})==sum(map(len,groups))
