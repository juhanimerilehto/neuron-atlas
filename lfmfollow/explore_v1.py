"""Finite exploratory stages: independent prompt partitions, frozen nominations and full journals."""
from concurrent.futures import ThreadPoolExecutor
import ctypes
import importlib
import json
import msvcrt
from pathlib import Path
import sys

import torch
from transformers import AutoTokenizer
from tokenizers import Tokenizer
from lfmfollow.core_v1 import ROOT, PROGRAM, PARENT, MODELS, Run, event, freeze, read, digest, other_jobs, JOB_LIMIT
from lfmfollow import review_v2
from lfmfollow.design_v1 import nominate
from lfmfollow.prompts_v1 import validate_partitions
from reference import fingerprint, write_json

BUILDERS = {'02-dose-response': 'study02_v1', '03-missed-candidates': 'study03_v1',
            '04-timing-operators': 'study04_v1', '05-neuron-pairs': 'study05_v1'}


def preflight(directory, plan):
    path = directory / 'preflight.json'
    if path.exists():
        assert read(path)['passed']
        return
    parent = PROGRAM / 'stages/01-confirm-p9/preflight.json'
    assert read(parent)['passed']
    original = read(PARENT / 'original/model.json')
    tok = AutoTokenizer.from_pretrained(original['snapshot'], local_files_only=True, trust_remote_code=False)
    prompts = sum(plan['prompts'].values(), [])
    for name in MODELS:
        info = read(PARENT / name / 'model.json')
        backend = Tokenizer.from_file(str(Path(info['snapshot']) / 'tokenizer.json'))
        assert backend.get_vocab(with_added_tokens=True) == tok.get_vocab()
        for prompt in prompts:
            text = tok.apply_chat_template([{'role': 'user', 'content': prompt}], tokenize=False,
                add_generation_prompt=True, enable_thinking=False, thinking=False)
            assert backend.encode(text, add_special_tokens=False).ids == tok(text, add_special_tokens=False).input_ids
    record = {'passed': True, 'native_preflight_sha256': digest(parent), 'prompt_tokenizations_per_checkpoint': len(prompts),
              'scope': 'Reuses unchanged native family actor and pinned weights; checks new prompt tokenization.'}
    if plan.get('actor_module') == 'lfmfollow.timed_actor_v1':
        timed = PROGRAM / plan.get('timing_preflight_file', 'timing-preflight-v2.json')
        report = read(timed)
        assert report['passed'] and report['actor_source_sha256'] == digest(ROOT / 'lfmfollow/timed_actor_v1.py')
        record.update(timing_preflight_sha256=digest(timed), scope='Native timing/operator conformance plus new prompt tokenization.')
    write_json(path, record)


class Study(Run):
    def expected(self, phase, count):
        path = self.directory / 'expected-counts.json'
        value = read(path) if path.exists() else {}
        if phase in value:
            assert value[phase] == count
        value[phase] = count
        write_json(path, value)

    def generate_variants(self, phase, variants, prompts, limit, controls=False):
        self.expected(phase, len(variants) * len(prompts) * (4 if controls else 1))
        result = {}
        for name in MODELS:
            path = self.directory / name / (phase + '.json')
            if path.exists():
                result[name] = read(path)
                continue
            pairs = {v['component']: [] for v in variants}
            for index, prompt in enumerate(prompts):
                configs = []
                for variant in variants:
                    first = variant['sites'][0]
                    value = first['value']
                    for random_index in (range(4) if controls else [None]):
                        cfg = {'coordinate': variant['component'], 'layer': first['layer'], 'neuron': first['neuron'],
                            'prompt': prompt, 'setting': variant['id'], 'condition': 'off' if value == 0 else 'positive' if value > 0 else 'negative',
                            'factor': abs(value), 'stage': phase, 'max_tokens': limit, 'type': 'generation',
                            'sites': variant['sites'], 'timing': variant['timing'], 'variant': variant}
                        if random_index is not None:
                            cfg['random_index'] = random_index
                        configs.append(cfg)
                values = self.execute(name, configs)
                for cfg, raw in zip(configs, values):
                    baseline = raw['batch_baseline']
                    pairs[cfg['coordinate']].append({'id': fingerprint({'identity': fingerprint({'parent': self.identity, 'model': name}), 'config': cfg}),
                        'config': cfg, 'prompt': prompt, 'condition': cfg['setting'], 'stage': phase,
                        'kind': 'random_direction' if controls else 'neuron', 'random_index': cfg.get('random_index'),
                        'baseline': baseline['text'], 'steered': raw['text'], 'termination': raw['termination'],
                        'token_ids': raw['token_ids'], 'baseline_token_ids': baseline['token_ids'], 'intervention': raw['intervention']})
                self.progress(phase, model=name, prompts_complete=index + 1, prompts_total=len(prompts))
            write_json(path, pairs); result[name] = pairs
        return result

    def review_phase(self, phase, cases, hypotheses=None, independent=False):
        folder = self.directory / ('confirmations' if independent else 'reviews') / phase
        folder.mkdir(parents=True, exist_ok=True)
        reviewer = self.confirmation if independent else self.reviewer
        jobs = []
        chunk_size = 3 if hypotheses else 16
        for component in cases['original']:
            conditions = sorted({p['condition'] for p in cases['original'][component] if p['kind'] == 'neuron'})
            for offset in range(0, len(conditions), chunk_size):
                key = component + '-part' + str(offset // chunk_size)
                jobs.append((key, component, conditions[offset:offset + chunk_size]))
        raw_reviews, failures = {}, []
        def one(job):
            key, component, conditions = job
            bundle = review_v2.bundle(self.directory.name + '_' + phase + '_' + key, component, cases, conditions, hypotheses)
            try:
                value = reviewer.review(bundle)
                write_json(folder / (key + '.json'), value)
                return key, value, None
            except RuntimeError as error:
                if str(error) != 'Two review attempts failed validation; original evidence retained':
                    raise
                failure = {'group': key, 'phase': phase, 'component': component, 'conditions': conditions,
                           'independent': independent, 'requested_model': reviewer.model, 'status': 'review_unavailable', 'reason': str(error)}
                write_json(self.directory / 'review-failures' / (('sol-' if independent else 'terra-') + phase + '-' + key + '.json'), failure)
                return key, None, failure
        with ThreadPoolExecutor(max_workers=2) as pool:
            for key, value, failure in pool.map(one, jobs):
                if value:
                    raw_reviews[key] = value
                if failure:
                    failures.append(failure)
                self.progress('codex_' + phase, accepted=len(raw_reviews), rejected=len(failures), total=len(jobs), independent=independent)
        if jobs and not raw_reviews:
            raise RuntimeError('No accepted reviews in this phase; saved failures need diagnosis')
        merged = {name: {} for name in MODELS}
        for record in raw_reviews.values():
            for item in record['analysis']['items']:
                alias, component = item['component_id'].split('__', 1)
                name = {'A': 'original', 'B': 'abliterated'}[alias]
                for effect in item['condition_effects']:
                    rows = [p for p in cases[name][component] if p['kind'] == 'neuron' and p['condition'] == effect['condition']]
                    target = merged[name].setdefault(component, {})
                    assert effect['condition'] not in target
                    target[effect['condition']] = {'effect': effect, 'n': len(rows),
                        'hits': len({p['id'] for p in rows} & set(effect['matching_ids'])),
                        'review_input_sha256': record['input_sha256'], 'followup_tests': item['followup_tests']}
        write_json(self.directory / 'analyses' / (('sol-' if independent else '') + phase + '.json'), merged)
        return merged, raw_reviews


def combine(phases):
    result = {name: {} for name in MODELS}
    for phase in phases.values():
        for name, components in phase.items():
            for component, pairs in components.items():
                result[name].setdefault(component, []).extend(pairs)
    return result


def frozen_file(path, value):
    if path.exists():
        assert read(path) == value, 'Adaptive stage selection changed during recovery'
    else:
        write_json(path, value)


def run_stage(stage_id):
    builder_name = BUILDERS[stage_id]
    builder = importlib.import_module('lfmfollow.' + builder_name)
    plan = builder.build()
    directory = PROGRAM / 'stages' / stage_id
    directory.mkdir(parents=True, exist_ok=True)
    if (directory / 'independent-audit.json').exists() and read(directory / 'independent-audit.json')['passed']:
        print('Completed stage audit retained.', flush=True); return
    validate_partitions(); preflight(directory, plan)
    assert all(other_jobs(directory, name) + plan['budget_upper_bound_per_checkpoint'] <= JOB_LIMIT for name in MODELS)
    sources = ['lfmfollow/explore_v1.py', 'lfmfollow/design_v1.py', 'lfmfollow/prompts_v1.py',
               'lfmfollow/review_v2.py', 'lfmfollow/' + builder_name + '.py']
    if plan.get('actor_module') == 'lfmfollow.timed_actor_v1':
        sources += ['lfmfollow/timed_actor_v1.py', 'lfmfollow/preflight_timing_v2.py']
    manifest, models = freeze(directory, plan, sources)
    run = Study(directory, manifest, models)
    prompts = plan['prompts']; initial = plan['variants']
    phases = {'discovery': run.generate_variants('discovery', initial, prompts['discovery'], 128)}
    discovery, raw_discovery = run.review_phase('discovery', phases['discovery'])
    if hasattr(builder, 'select_validation'):
        validation_variants, ranking = builder.select_validation(discovery, initial)
    else:
        validation_variants, ranking = nominate(discovery, initial, 8, 4, seed=plan['seed'])
    frozen_file(directory / 'validation-plan.json', {'variants': validation_variants, 'ranking': ranking})
    phases['validation'] = run.generate_variants('validation', validation_variants, prompts['validation'], 192)
    validation, raw_validation = run.review_phase('validation', phases['validation'])
    if hasattr(builder, 'select_final'):
        finalists, final_ranking = builder.select_final(validation, validation_variants)
    else:
        finalists, final_ranking = nominate(validation, validation_variants, 4, 2, seed=plan['seed'] + 1)
    frozen_file(directory / 'frozen-finalists.json', {'variants': finalists, 'ranking': final_ranking})
    hypotheses = builder.freeze_hypotheses(finalists, validation) if hasattr(builder, 'freeze_hypotheses') else {name: {} for name in MODELS}
    for variant in ([] if hasattr(builder, 'freeze_hypotheses') else finalists):
        component, condition = variant['component'], variant['id']
        fallback = next((validation[name].get(component, {}).get(condition) for name in MODELS
                         if validation[name].get(component, {}).get(condition, {}).get('effect', {}).get('label')), None)
        assert fallback
        for name in MODELS:
            own = validation[name].get(component, {}).get(condition)
            effect = own['effect'] if own and own['effect']['label'] else fallback['effect']
            hypotheses[name].setdefault(component, []).append({'condition': condition, 'label': effect['label']})
    frozen_file(directory / 'frozen-hypotheses.json', hypotheses)
    for phase, limit in [('locked_test', 256), ('long', 384), ('replication', 256)]:
        phases[phase] = run.generate_variants(phase, finalists, prompts[phase], limit)
    phases['random_controls'] = run.generate_variants('random_controls', finalists, prompts['locked_test'][:8], 256, True)
    final_cases = combine({k: v for k, v in phases.items() if k in ('locked_test', 'long', 'replication', 'random_controls')})
    final, raw_final = run.review_phase('locked_test', final_cases, hypotheses)
    independent, raw_independent = run.review_phase('locked_test', final_cases, hypotheses, True)
    all_cases = combine(phases); write_json(directory / 'pairs.json', all_cases)
    expected = {k: v for k, v in read(directory / 'expected-counts.json').items() if v}
    audit = run.audit(all_cases, {**{'discovery-' + k: v for k, v in raw_discovery.items()},
        **{'validation-' + k: v for k, v in raw_validation.items()}, **raw_final}, raw_independent, expected)
    audit['review_gaps'] = [read(p) for p in (directory / 'review-failures').glob('*.json')]
    write_json(directory / 'independent-audit.json', audit)
    event(directory, 'measurements_complete', review_gaps=len(audit['review_gaps']), next_action='Export assessed observations and queue public publication.')


def main():
    stage_id = sys.argv[1]; assert stage_id in BUILDERS
    directory = PROGRAM / 'stages' / stage_id; directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.lock').open('a+b') as lock:
        lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        awake = ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
        try:
            torch.set_num_threads(4); torch.backends.cuda.matmul.allow_tf32 = False; torch.manual_seed(2026112700 + int(stage_id[:2]))
            run_stage(stage_id)
        except BaseException as error:
            event(directory, 'failed', error_type=type(error).__name__, error=str(error)); raise
        finally:
            if awake: ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == '__main__':
    main()
