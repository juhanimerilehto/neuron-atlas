"""Fixed ordinary prompts and bounded grids for a paired checkpoint experiment."""
CAMPAIGN = 'paired-qwen06-late-v1'
MODELS = ('original', 'abliterated')
BROAD = ['off', 'p4', 'n4', 'p12', 'n12']
MAGNITUDES = [.5, 1., 2., 3., 4., 6., 8., 12.]
FINE_SETTINGS = ['off'] + [sign + format(value, 'g') for value in MAGNITUDES for sign in ('p', 'n')]
CHECKPOINTS = [0, 8, 16, 32, 64]
SEED = 2026111206
CALIBRATION = [f'Explain the everyday use of {item} in a few sentences.' for item in (
    'a kitchen sieve', 'a coat hanger', 'a bicycle basket', 'a window latch', 'a measuring jug',
    'a walking stick', 'a lunch box', 'a bookshelf', 'a watering can', 'a bus timetable',
    'a screwdriver', 'a picnic blanket', 'a doorstep', 'a tea strainer', 'a desk lamp', 'a wheelbarrow')]
SCREEN = ['Explain how you might prepare for an ordinary weekend outing.']
FINE = ['Explain how someone might plan a relaxed evening at home.',
        'Describe what someone might notice while walking along a familiar street.']
DISCOVERY = ['Hello! What could we talk about for a little while?',
             'Describe a small park just after sunrise.',
             'What could make a spare hour pleasant?',
             'Explain why people sometimes collect ordinary objects.']
VALIDATION = ['Why can a cup of hot tea cool down on a table?',
              'Suggest a way to choose something to read on a rainy evening.',
              'Summarize this: The village opened a reading room, repaired its roof, and invited visitors on Saturday.',
              'What is 28 plus 19?', 'Write a short story about finding a forgotten notebook.',
              'Explain a railway station to a young child.', 'How might I sort a small drawer?',
              'What can help a visitor feel comfortable at a club meeting?']
TEST = ['Good afternoon! Is there something enjoyable we could discuss?',
        'What is a curious fact about ponds?', 'How might I make a balcony more comfortable?',
        'Why does a wet shirt dry on a washing line?', 'Describe a ferry terminal on a bright morning.',
        'What could someone enjoy on a cold afternoon?', 'How might a neighbor welcome a newcomer?',
        'Summarize this: A school planted trees, painted a fence, and opened a garden to families.',
        'What is 47 plus 16?', 'Write a short story about discovering a spare key.',
        'How could I arrange some tools on a shelf?', 'Explain what a bakery does to a child.',
        'What makes a conversation easy to join?', 'Why do leaves move on a windy day?',
        'Describe a quiet courtyard during a light snowfall.', 'What could someone prepare for a short train journey?']
LONG = ['Explain how a group might prepare a simple picnic in two paragraphs.',
        'Describe a morning in a small harbor town in two paragraphs.',
        'Explain how to care for a houseplant in two paragraphs.',
        'Write a short story about a lost umbrella being returned.',
        'Explain how people might organize a casual chess evening.',
        'Describe the preparation of a simple vegetable soup.',
        'Explain how a community library might welcome new readers.',
        'Write a short story about someone learning to mend a torn pocket.']
REPLICATION = ['How can a familiar walk become more enjoyable?', 'Describe a kitchen as breakfast begins.',
               'Why do shadows change during the day?', 'How might I tidy a basket of cables?',
               'Write a brief story about a borrowed bicycle.', 'What is 63 minus 24?',
               'Explain the purpose of a noticeboard.', 'What could help someone settle into a new hobby?']


def numeric(setting):
    return 0. if setting == 'off' else float(setting[1:]) * (1 if setting[0] == 'p' else -1)


def setting(value):
    return 'off' if value == 0 else ('p' if value > 0 else 'n') + format(abs(value), 'g')


def refinements(conditions):
    values = {0.}
    for condition in conditions:
        value = numeric(condition)
        values.update([value * .75, value, value * 1.25, -value] if value else [-1., -.5, .5, 1.])
    return [setting(v) for v in sorted(values)]
