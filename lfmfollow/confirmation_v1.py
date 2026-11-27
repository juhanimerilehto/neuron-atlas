"""First preregistered follow-up: the previously untested +9x diplomatic setting."""
import ctypes
import msvcrt
import torch
from lfmfollow.core_v1 import PROGRAM, Run, event, freeze, read
from reference import write_json

STAGE = PROGRAM / 'stages/01-confirm-p9'
TEST = [
    'Why does a metal spoon feel colder than a wooden spoon in the same room?',
    'How could someone arrange a pleasant afternoon with an old friend?',
    'Describe a grocery shop shortly before closing time.',
    'What is 36 plus 27?',
    'Summarize this: The museum repaired its clock, updated the signs, and welcomed school groups on Monday.',
    'Why might a spider web be easier to see on a misty morning?',
    'Write a short story about a postcard arriving at the wrong address.',
    'How could I keep a few recipes easy to find?',
    'What makes a good place to read outdoors?',
    'Explain the purpose of a door hinge in everyday language.',
    'Describe the sounds in a busy swimming pool.',
    'What is 84 minus 37?',
    'How might someone welcome a friend who has moved back to town?',
    'Why can a puddle reflect the sky?',
    'Write a brief story about finding a familiar song on an old radio.',
    'What could we talk about during a quiet bus ride?',
]
LONG = [
    'Explain how to prepare a small balcony for spring in two paragraphs.',
    'Describe an afternoon at a village fair in two paragraphs.',
    'Write a short story about someone restoring a worn photograph.',
    'Explain the journey of bread from a bakery oven to a family breakfast.',
    'Describe how a group of friends could organize a relaxed board-game afternoon.',
    'Write a short story about an unexpected visitor to a watch repair shop.',
    'Explain how someone could learn to identify common birds in a local park.',
    'Describe how an old market square changes from morning to evening.',
]
REPLICATION = [
    'Why does a freshly washed window sometimes show streaks?',
    'Suggest a simple way to remember a few appointments.',
    'Describe a small bookshop during a rainy lunch hour.',
    'What is 18 multiplied by 4?',
    'Write a short story about a missing button being found.',
    'Explain why a bicycle needs a chain.',
    'How could someone make a shared meal welcoming?',
    'What might be enjoyable about visiting a botanical garden?',
]
PLAN = {
    'public_preregistration_required': True,
    'kind': 'prospective_confirmation', 'coordinate': 'L2-N3420', 'settings': {'L2-N3420': ['p9']},
    'frozen_description': 'Diplomatic and military reframing',
    'hypothesis_scope': 'Ordinary questions are reinterpreted through diplomacy, military strategy, security or international relations.',
    'prior_evidence': 'paired-lfm25-350m-v1 validation at p9. No p9 held-out result existed. Earlier scores and notes are withheld from the new reviewers.',
    'prompts': {'locked_test': TEST, 'long': LONG, 'replication': REPLICATION, 'random_controls': TEST[:8]},
    'token_limits': {'locked_test': 256, 'long': 384, 'replication': 256, 'random_controls': 256},
    'expected_counts_per_checkpoint': {'locked_test': 16, 'long': 8, 'replication': 8, 'random_controls': 32},
    'gate': {'change_min': 3, 'coherence_min': 3, 'heldout_matches_min': 8, 'long_matches_min': 4,
             'replication_matches_min': 4, 'repetition_max': 2, 'collapse_max': 2, 'both_reviewers_required': True},
    'interpretation': 'Task loss and baseline defects are reported separately. Random specificity is descriptive, not a gate requirement. '
    'Only this frozen dose/description is confirmatory; later dose or timing searches are exploratory until independently tested.'}


def main():
    from familylab import data
    previous = sum([getattr(data, key) for key in ('CALIBRATION', 'SCREEN', 'FINE', 'DISCOVERY', 'VALIDATION', 'TEST', 'LONG', 'REPLICATION')], [])
    fresh = TEST + LONG + REPLICATION
    assert len(fresh) == len(set(p.casefold().strip() for p in fresh)) == 32
    assert not set(p.casefold().strip() for p in fresh) & set(p.casefold().strip() for p in previous)
    STAGE.mkdir(parents=True, exist_ok=True)
    with (STAGE / '.lock').open('a+b') as lock:
        lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        awake = ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
        try:
            torch.set_num_threads(4); torch.backends.cuda.matmul.allow_tf32 = False; torch.manual_seed(2026112701)
            manifest, models = freeze(STAGE, PLAN, ['lfmfollow/confirmation_v1.py', 'lfmfollow/preflight_v1.py'])
            run = Run(STAGE, manifest, models)
            phases = {phase: run.generate_phase(phase, PLAN['settings'], prompts,
                PLAN['token_limits'][phase], phase == 'random_controls') for phase, prompts in PLAN['prompts'].items()}
            cases = {name: {'L2-N3420': sum([phase[name]['L2-N3420'] for phase in phases.values()], [])}
                     for name in ('original', 'abliterated')}
            write_json(STAGE / 'pairs.json', cases)
            hypotheses = {'L2-N3420': [{'condition': 'p9', 'label': PLAN['frozen_description'], 'scope': PLAN['hypothesis_scope']}]}
            primary = run.assess('locked_test', cases, hypotheses)
            independent = run.assess('locked_test', cases, hypotheses, True)
            run.audit(cases, primary, independent, PLAN['expected_counts_per_checkpoint'])
            event(STAGE, 'measurements_complete', next_action='Prepare assessed outcomes and publication; do not overwrite historical observations.')
        except BaseException as error:
            event(STAGE, 'failed', error_type=type(error).__name__, error=str(error)); raise
        finally:
            if awake: ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == '__main__':
    main()
