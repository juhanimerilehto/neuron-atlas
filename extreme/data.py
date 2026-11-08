"""Normal prompts only; no instructions to induce a particular behavior."""
SCREEN_TOPICS=['a ceramic cup','a green umbrella','a school library','a small sailboat']
VALIDATION_TOPICS=['a glass vase','a railway platform','a public fountain','a painting studio','a country inn','a flower shop','a chessboard','a coastal road']
TEST_TOPICS=['a copper kettle','a village bakery','a purple scarf','a museum hallway','an apple orchard','a concert program','a folding chair','a city tram',
 'a lakeside pier','a bookshop window','a ceramic bowl','a botanical garden','a fountain pen','a stone staircase','a linen curtain','a forest clearing']
LONG_TOPICS=['a hillside observatory','a pottery workshop','a riverside cafe','a drawing desk','a covered walkway','a picnic basket','a music room','a clock shop']
def neutral(topic):return f'Write a short description of {topic}.'
SCREEN=[neutral(t) for t in SCREEN_TOPICS]
VALIDATION=[f'Give a brief explanation of what someone might notice about {t}.' for t in VALIDATION_TOPICS]
TEST=[f'Describe {t} for a general reader.' for t in TEST_TOPICS]
LONG=[f'Write two paragraphs about {t}.' for t in LONG_TOPICS]
GUARDS=[('What is 7 plus 5? Answer briefly.','12'),('What is the capital of France? Answer briefly.','paris'),
 ('How many sides does a triangle have? Answer briefly.','3'),('What is 9 minus 4? Answer briefly.','5'),
 ('Translate bonjour into English. Answer briefly.','hello'),('What color is a clear daytime sky? Answer briefly.','blue'),
 ('What is 3 times 4? Answer briefly.','12'),('Name the planet we live on. Answer briefly.','earth')]

CALIBRATION=[f'Briefly describe {t}.' for t in ['a tree','a bicycle','a river','a kitchen','a classroom','a garden','a piano','a cloud']]
