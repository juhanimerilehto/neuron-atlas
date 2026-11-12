"""Fresh paired-checkpoint reviews with the existing validated evidence contract."""
import copy
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('paired06_review_contract', ROOT / 'rereview/reviewer.py')
contract = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = contract
spec.loader.exec_module(contract)
original_compact = contract.compact


def compact(bundle):
    wire, mapping = original_compact(bundle)
    short = {}
    for item in wire['items']:
        for pair in item['pairs']:
            alias = f'E{len(short)}'
            short[alias] = mapping[pair['id']]
            pair['id'] = alias
            pair['identical_text'] = pair['steered'] == wire['baselines'][pair['baseline_ref']]
    wire['baseline_lookup'] = ('Compare each steered response with baselines[baseline_ref]. '
                               'Pairs marked identical_text=true cannot support ANY behavioral change. '
                               'Every E ID is reviewed exactly once. Baseline B IDs are lookup keys only.')
    return wire, short


contract.compact = compact
contract.INSTRUCTION = contract.INSTRUCTION.replace(
    'Reconsider behavioral changes without seeing earlier scores, novelty labels or selection outcomes.',
    'Analyze these NEW measured paired-checkpoint experiments without seeing prior catalogue labels or screen scores.')
contract.INSTRUCTION = contract.INSTRUCTION.replace(
    'a frozen nomination for this retrospective review', 'a hypothesis frozen before the current held-out test')
contract.INSTRUCTION = contract.INSTRUCTION.replace(
    'Reused validation and held-out data are retrospective evidence, not a new locked experiment.',
    'Stage metadata identifies discovery, validation, locked tests, longer continuations and replication. '
    'A paired component belongs to ONE pinned checkpoint. Compare every response only with its own paired baseline. '
    'The corresponding coordinate in the other checkpoint is assessed separately. '
    'A checkpoint name or the word abliterated is not evidence of a behavioral effect.')
Reviewer = contract.Reviewer
FIELDS = contract.FIELDS
validate = contract.validate


def bundle(phase, namespace, coordinates, pairs_by_model, settings, models, hypotheses=None):
    items = []
    for coordinate in coordinates:
        for model_name, model in models.items():
            cid = f'{model_name}__{coordinate}'
            pairs = pairs_by_model[model_name][coordinate]
            item = {'component_id': cid, 'model': model['repository'], 'revision': model['revision'],
                    'settings': settings[coordinate], 'pairs': pairs}
            if hypotheses:
                item['proposed_hypothesis'] = hypotheses[cid]
            items.append(item)
    return {'namespace': namespace, 'phase': phase, 'items': items,
            'scope': 'Same ordinary prompts and signed activation targets in two separately pinned checkpoints. '
                     'Each response has its own unmodified baseline. Targets use original-model calibration. '
                     'Change and coherence are independent ordinal judgments. Novelty has no selection weight.'}


def best(item, phase, pairs):
    effects = []
    for effect in item['condition_effects']:
        rows = [p for p in pairs if p['kind'] == 'neuron' and p['condition'] == effect['condition']
                and (phase != 'locked_test' or p['stage'] == 'locked_test')]
        row = copy.deepcopy(effect)
        row['n'] = len(rows)
        row['hits'] = len(set(effect['matching_ids']) & {p['id'] for p in rows})
        effects.append(row)
    readable = [e for e in effects if e['coherence'] >= 3]
    eligible = readable or effects
    return max(eligible, key=lambda e: (e['change_strength'], e['hits'] / max(1, e['n']),
                                       e['coherence'], -len(e['collapse_ids']), -len(e['repetition_ids'])))
