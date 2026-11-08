"""Boundary checks for the new evidence contract; no model calls."""
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'rereview'))
from reviewer import compact,expand,validate,FIELDS

class Tests(unittest.TestCase):
    def fixture(self):
        pairs=[{'id':'first','kind':'neuron','condition':'p2','baseline':'Hello','steered':'7 7 7 7'},
            {'id':'second','kind':'neuron','condition':'n2','baseline':'Hello','steered':'Dear recipient'},
            {'id':'control','kind':'random_direction','condition':'p2','baseline':'Hello','steered':'Hello'}]
        bundle={'namespace':'test','items':[{'component_id':'L7-N1','settings':['p2','n2'],'pairs':pairs}]}
        effects=[]
        for condition,label,key in [('p2','Numeric repetition','first'),('n2','Formal correspondence','second')]:
            effects.append({'condition':condition,'label':label,'change_strength':4,'coherence':0 if condition=='p2' else 4,
                **{field:[] for field in FIELDS},'note':'Observed change; finite sample.','hypothesis_supported':None})
            effects[-1]['matching_ids']=[key]
        result={'schema_version':'extremity-rereview.v1','reviewed_evidence_ids':['first','second','control'],
            'items':[{'component_id':'L7-N1','overview':'Two distinct modes by sign.','condition_effects':effects,'followup_tests':[]}]}
        return bundle,result
    def test_axes_independent(self):
        bundle,value=self.fixture();validate(value,bundle)
    def test_cross_condition_reference_rejected(self):
        bundle,value=self.fixture();value['items'][0]['condition_effects'][0]['matching_ids']=['second']
        with self.assertRaises(AssertionError):validate(value,bundle)
    def test_missing_condition_rejected(self):
        bundle,value=self.fixture();value['items'][0]['condition_effects'].pop()
        with self.assertRaises(AssertionError):validate(value,bundle)
    def test_unchanged_output_cannot_be_evidence(self):
        bundle,value=self.fixture();bundle['items'][0]['pairs'][0]['steered']='Hello'
        with self.assertRaises(AssertionError):validate(value,bundle)
    def test_deduplicated_baseline_and_lossless_references(self):
        bundle,value=self.fixture();original=copy.deepcopy(bundle);wire,mapping=compact(bundle)
        self.assertEqual(len(wire['baselines']),1);self.assertEqual(bundle,original)
        reverse={v:k for k,v in mapping.items()};raw=copy.deepcopy(value)
        raw['reviewed_evidence_ids']=[reverse[k] for k in value['reviewed_evidence_ids']]
        for e in raw['items'][0]['condition_effects']:
            for field in FIELDS:e[field]=[reverse[k] for k in e[field]]
        validate(raw,wire);self.assertEqual(expand(raw,mapping),value)

if __name__=='__main__':unittest.main()
