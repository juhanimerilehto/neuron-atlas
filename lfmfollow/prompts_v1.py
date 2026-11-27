"""Fixed ordinary-task partitions for four follow-ups; shared templates are disclosed."""
SCIENCE = [
    'Why does a ceramic cup sometimes crack when heated suddenly?', 'Why does a compass needle turn?',
    'Why can a balloon stick to a wall after being rubbed?', 'Why do stars appear to twinkle?',
    'Why does ice float in a glass of water?', 'Why does a rainbow have several colors?',
    'Why does a stretched rubber band return toward its original shape?', 'Why do some seeds travel on the wind?',
    'Why does a mirror fog up in a bathroom?', 'Why do apples become brown after being cut?',
    'Why does a magnet attract a paper clip?', 'Why do some birds migrate each year?',
    'Why does a shadow look blurry at its edge?', 'Why can a straw appear bent in water?',
    'Why does sugar dissolve faster in warm water?', 'Why can sound echo in an empty hall?',
    'Why do some flowers close at night?', 'Why does a spinning top eventually fall?',
    'Why does frost form on a car window?', 'Why do soap bubbles often look round?',
    'Why does a guitar string change pitch when tightened?', 'Why can a sunflower turn toward light?',
    'Why does a glass of cold water collect droplets outside?', 'Why does a spring compress under a weight?',
    'Why does a candle flame usually point upward?', 'Why does sand feel different from wet clay?',
    'Why does a seesaw move when one person shifts position?', 'Why do some stones look darker when wet?']
PRACTICAL = [
    'How could I organize a box of art supplies?', 'How might someone plan a low-key birthday breakfast?',
    'How could I keep track of borrowed books?', 'How might I prepare for a short nature walk?',
    'How could someone start a small windowsill herb garden?', 'How might I store photographs neatly?',
    'How could I make a small desk easier to use?', 'How might someone choose a gift for a keen baker?',
    'How could I organize a cupboard of mugs?', 'How might someone prepare for a first pottery class?',
    'How could I plan a relaxed afternoon with cousins?', 'How might I make a guest room comfortable?',
    'How could I keep a collection of postcards tidy?', 'How might someone prepare for a local walking tour?',
    'How could I sort a pile of spare fabric?', 'How might I plan snacks for a casual film evening?',
    'How could someone look after a borrowed houseplant?', 'How might I arrange a shelf of picture frames?',
    'How could I make a hobby corner pleasant?', 'How might someone pack for a weekend at a cottage?',
    'How could I label a collection of small jars?', 'How might I prepare for a beginner drawing lesson?',
    'How could someone keep gardening gloves easy to find?', 'How might I organize notes from a class?',
    'How could I prepare a small basket for a beach visit?', 'How might someone arrange a drawing table?',
    'How could I keep a set of reusable shopping bags handy?', 'How might I organize a drawer of baking tools?']
SCENES = [
    'a flower stall opening for the day', 'an old cinema foyer on a quiet afternoon', 'a beach after a gentle rain',
    'a village bakery before breakfast', 'a greenhouse full of seedlings', 'a campsite as evening arrives',
    'a train carriage during a sunny morning', 'a craft shop with an open front door', 'a footbridge over a slow stream',
    'a kitchen while biscuits are cooling', 'a fishing pier before dawn', 'a quiet museum gallery',
    'a city fountain during lunch hour', 'a small theatre before a rehearsal', 'a garden path covered in autumn leaves',
    'a station cafe after the morning rush', 'a workshop where a chair is being repaired', 'a field after the hay has been cut',
    'a courtyard with washing hanging above it', 'a public reading room on a winter morning', 'a hillside orchard in blossom',
    'a cafe terrace after a sudden shower', 'a toy shop window during the holidays', 'a quiet pier at sunset',
    'a farmyard as the hens are fed', 'a town bandstand on a summer evening', 'a hallway filled with winter coats', 'a bridge lit by lanterns']
STORIES = [
    'a pair of gloves left on a cafe chair', 'a small parcel with a smudged address', 'a painted stone found on a path',
    'a bicycle bell heard outside a workshop', 'a lamp being repaired for a neighbor', 'a family recipe discovered in a cupboard',
    'a ticket found inside a secondhand coat', 'a dog bringing home a knitted hat', 'a sketchbook returned to its owner',
    'a gardener finding a tiny clay figure', 'a child learning to fly a paper kite', 'a familiar tune played on a street corner',
    'a broken clock beginning to work again', 'a traveler recognizing a childhood shop', 'a basket being delivered to the wrong house',
    'an old camera containing one last photograph', 'a visitor finding a handwritten recipe card', 'a missing scarf appearing on a fence',
    'a carpenter making a small wooden boat', 'a cat sleeping in a newly planted flowerpot', 'a baker experimenting with a new loaf',
    'a postcard arriving many years late', 'a child finding a tiny brass bell', 'a repaired umbrella being given away',
    'a map drawn by a child for a grandparent', 'a basket of apples appearing at a doorstep',
    'a musician lending an old instrument', 'a new baker learning a favorite family recipe']
OBJECTS = ['a bicycle pump', 'a kitchen whisk', 'a rain gauge', 'a bookend', 'a folding ruler', 'a garden trowel',
           'a clothes peg', 'a magnifying glass', 'a cork stopper', 'a sewing thimble', 'a doorstop', 'a luggage tag',
           'a spirit level', 'a cheese grater', 'a bird feeder', 'a watering tray', 'a pencil sharpener', 'a shoehorn',
           'a kitchen funnel', 'a bookmark', 'a wind chime', 'a bicycle stand', 'a rolling pin', 'a sieve used for flour',
           'a hand rake', 'a camping lantern', 'a soap dish', 'a bicycle reflector']
INTERESTS = ['watching clouds', 'visiting a local orchard', 'learning to fold paper', 'listening to a street musician',
             'exploring a secondhand bookshop', 'taking pictures of doorways', 'collecting fallen leaves', 'visiting a small aquarium',
             'trying a new soup recipe', 'walking beside a canal', 'learning a simple card game', 'watching birds from a window',
             'visiting an old lighthouse', 'sketching ordinary kitchen objects', 'listening to records', 'learning about local trees',
             'looking through a family photo album', 'visiting a small railway museum', 'growing tomatoes', 'learning a few dance steps',
             'exploring a flea market', 'watching a sunrise', 'learning to mend socks', 'visiting a sculpture garden',
             'making a simple collage', 'visiting a mill', 'growing a bean plant', 'learning a new folk song']
PLACES = ['bakery', 'art studio', 'swimming club', 'repair cafe', 'music shop', 'plant nursery',
          'local museum', 'cafe', 'garden center', 'library annex', 'craft workshop', 'animal shelter',
          'community kitchen', 'pottery studio', 'bookshop', 'sports hall', 'bicycle shop', 'small theatre',
          'flower shop', 'model railway club', 'photography group', 'village shop', 'sewing class', 'drawing club',
          'local aquarium', 'chess club', 'garden workshop', 'ceramics class']


def partition(index):
    assert index in range(4)
    categories = [SCIENCE, PRACTICAL, ['Describe ' + x + '.' for x in SCENES],
        [f'Calculate {31 + (i * 7) % 56} plus {12 + (i * 11) % 37}.' for i in range(28)],
        [f'Summarize this note: The {x} changed its opening hours, repaired the front steps, and invited visitors on Friday.' for x in PLACES],
        ['Write a short story about ' + x + '.' for x in STORIES],
        ['Explain the everyday purpose of ' + x + '.' for x in OBJECTS],
        ['What could be enjoyable about ' + x + '?' for x in INTERESTS]]
    rows = [[category[index * 7 + offset] for category in categories] for offset in range(7)]
    return {'discovery': rows[0] + rows[1], 'validation': rows[2], 'locked_test': rows[3] + rows[4],
            'long': [p + ' Give a connected answer in two paragraphs.' for p in rows[5]], 'replication': rows[6]}


def validate_partitions():
    from familylab import data
    from lfmfollow.confirmation_v1 import TEST, LONG, REPLICATION
    old = sum([getattr(data, k) for k in ('CALIBRATION', 'SCREEN', 'FINE', 'DISCOVERY', 'VALIDATION', 'TEST', 'LONG', 'REPLICATION')], [])
    prior = {p.casefold().strip() for p in old + TEST + LONG + REPLICATION}
    fresh = [p for i in range(4) for prompts in partition(i).values() for p in prompts]
    assert len(fresh) == len(set(p.casefold().strip() for p in fresh)) == 224
    assert not prior & {p.casefold().strip() for p in fresh}
    return True
