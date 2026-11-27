"""Freeze the first confirmation for public preregistration without creating any jobs."""
from lfmfollow.core_v1 import freeze
from lfmfollow.confirmation_v1 import STAGE, PLAN

if __name__ == '__main__':
    value, _ = freeze(STAGE, PLAN, ['lfmfollow/confirmation_v1.py', 'lfmfollow/preflight_v1.py'])
    print('Confirmation frozen; no measurement jobs created.', flush=True)
