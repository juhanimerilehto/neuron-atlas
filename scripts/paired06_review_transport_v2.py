"""Lossless text-evidence transport; numerical arrays remain in the raw bundle."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'worker')]
from paired06 import analysis

VERSION = 'paired06.review-transport.v2'
original_compact = analysis.compact
OMIT = {'token_ids', 'baseline_token_ids', 'intervention', 'diagnostics'}


def compact(bundle):
    wire, mapping = original_compact(bundle)
    if bundle.get('transport_version') == VERSION:
        for item in wire['items']:
            for pair in item['pairs']:
                for field in OMIT:
                    pair.pop(field, None)
    return wire, mapping


analysis.compact = compact
analysis.contract.compact = compact


def versioned(bundle):
    return {**bundle, 'namespace': bundle['namespace'] + '_transport_v2', 'transport_version': VERSION}


class TransportReviewer(analysis.Reviewer):
    def review(self, bundle):
        contract = analysis.contract
        key = contract.fingerprint({'bundle': bundle, 'instruction': contract.INSTRUCTION,
                                    'schema': contract.schema(), 'model': self.model, 'effort': 'medium'})
        if (self.directory / (key + '.analysis.json')).exists():
            return super().review(bundle)
        requests = list(self.directory.glob(key + '.attempt-*.request.json'))
        transport_failure = any('input_too_large' in p.read_text(encoding='utf-8')
                                for p in self.directory.glob(key + '.attempt-*.stderr.log'))
        if requests and not transport_failure:
            # Preserve the original attempt ceiling for non-transport failures.
            return super().review(bundle)
        revised = versioned(bundle)
        wire, _ = compact(revised)
        prompt = contract.INSTRUCTION + '\nEVIDENCE:\n' + __import__('json').dumps(wire, ensure_ascii=False)
        assert len(prompt) < 950000, 'Text evidence still too large; requires another audited transport design'
        return super().review(revised)
