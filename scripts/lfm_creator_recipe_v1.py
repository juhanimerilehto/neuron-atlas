"""Describe the pinned creator recipe and compare its layer windows with observed tensor edits."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / 'campaigns/lfm-depth-20261127-v1'
PARENT = ROOT / 'campaigns/paired-lfm25-350m-v1'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = PROGRAM / 'posthoc-creator-recipe-v1.json'
    if target.exists():
        assert read(target)['analysis_source_sha256'] == sha(Path(__file__))
        print('Existing creator-recipe audit retained.'); return
    model = read(PARENT / 'abliterated/model.json')
    source = Path(model['snapshot']) / 'reproduce'
    config = tomllib.loads((source / 'config.toml').read_text(encoding='utf-8'))
    reproduction = read(source / 'reproduce.json')
    parameters = reproduction['parameters']
    geometry = read(PROGRAM / 'posthoc-weight-geometry-v2.json')
    observed = {'attn.o_proj':[], 'mlp.down_proj':[]}
    for tensor in geometry['named_tensor_comparison']:
        if tensor['exact_equal']: continue
        key = tensor['tensor']; layer = int(re.match(r'model\.layers\.(\d+)\.', key)[1])
        group = 'mlp.down_proj' if key.endswith('feed_forward.w2.weight') else 'attn.o_proj'
        assert group == 'mlp.down_proj' or key.endswith(('.self_attn.out_proj.weight','.conv.out_proj.weight'))
        observed[group].append(layer)
    predicted = {group:[layer for layer in range(16) if abs(layer-settings['max_weight_position']) <= settings['min_weight_distance']]
        for group,settings in parameters['abliteration_parameters'].items()}
    for layers in observed.values(): layers.sort()
    upstream = {'repository':'p-e-w/heretic', 'tag':'v1.4.0', 'commit':'6ea3b8d778d047b4b3b7c5b843e21c5bea98ee8d',
        'path':'src/heretic/model.py', 'git_blob_sha':'3ea72fc9b3e7d61e61e0a71e121294a30dfd8c35',
        'url':'https://github.com/p-e-w/heretic/blob/6ea3b8d778d047b4b3b7c5b843e21c5bea98ee8d/src/heretic/model.py',
        'relevant_lines':{'layer_window_and_layer_direction':[484,507], 'row_normalization_and_adapter':[552,593]}}
    result = {'analysis_kind':'Post hoc creator-metadata audit; does not reproduce training or measure refusal.',
        'created_at_utc':datetime.now(timezone.utc).isoformat(), 'analysis_source_sha256':sha(Path(__file__)),
        'source_model_revision':model['revision'], 'creator_config_sha256':sha(source/'config.toml'),
        'creator_reproduction_sha256':sha(source/'reproduce.json'), 'geometry_sha256':sha(PROGRAM/'posthoc-weight-geometry-v2.json'),
        'creator_settings':{k:config[k] for k in ('orthogonalize_direction','row_normalization','full_normalization_lora_rank','winsorization_quantile')},
        'selected_parameters':parameters, 'predicted_changed_layers':predicted,'observed_changed_layers':observed,
        'layer_windows_match':predicted==observed, 'direction_selection':'layer-specific' if parameters['direction_index'] is None else 'shared/interpolated',
        'pinned_upstream_implementation':upstream,
        'interpretation':'The selected null direction_index uses per-layer directions in the pinned implementation. Full row normalization and a rank-three approximation are recorded, so a basic single orthogonal-projector fit is not a complete reconstruction of this recipe. Matching edit locations and low-rank geometry do not independently validate the creator benchmark or identify a causal refusal feature.'}
    temporary = target.with_suffix('.json.tmp'); temporary.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); temporary.replace(target)
    print(json.dumps({'layer_windows_match':result['layer_windows_match'],'direction_selection':result['direction_selection'],
        'changed_layers':observed,'creator_settings':result['creator_settings']}))


if __name__ == '__main__': main()
