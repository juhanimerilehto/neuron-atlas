"""Freeze the existing pair design for public registration, without constructing a worker."""
from datetime import datetime, timezone
import msvcrt
from pathlib import Path
import sqlite3

from lfmfollow.core_v1 import PROGRAM, MODELS, JOB_LIMIT, read, digest, freeze, other_jobs, event
from lfmfollow.explore_v1 import preflight
from lfmfollow.prompts_v1 import validate_partitions
from lfmfollow.study05_v1 import build
from reference import fingerprint, write_json


def main():
    directory = PROGRAM/'stages/05-neuron-pairs'
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'.lock').open('a+b') as lock:
        lock.seek(0); msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        try:
            assert read(PROGRAM/'status.json')['current_stage'] == '04-timing-operators'
            counts = {}
            for name in MODELS:
                path = directory/name/'jobs.sqlite'
                counts[name] = 0
                if path.exists():
                    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
                        counts[name] = db.execute('SELECT count(*) FROM jobs').fetchone()[0]
            assert not any(counts.values()), 'Public registration must precede every pair measurement'
            plan = build()
            validate_partitions(); preflight(directory,plan)
            assert all(other_jobs(directory,n)+plan['budget_upper_bound_per_checkpoint'] <= JOB_LIMIT for n in MODELS)
            sources = ['lfmfollow/explore_v1.py','lfmfollow/design_v1.py','lfmfollow/prompts_v1.py',
                'lfmfollow/review_v2.py','lfmfollow/study05_v1.py',
                'lfmfollow/timed_actor_v1.py','lfmfollow/preflight_timing_v2.py']
            manifest,_ = freeze(directory,plan,sources)
            record = {'stage_id':directory.name,'manifest_identity':fingerprint(manifest),
                'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'jobs_present_before_registration':counts,
                'registration_source_sha256':digest(Path(__file__)),
                'scope':'The existing pair design and measurement sources are unchanged. No Run, model generator or reviewer was constructed. Public deployment and a zero-job check must be recorded separately before claiming public registration.'}
            path = directory/'premeasurement-registration.json'
            assert not path.exists(), 'Retain the first registration record'
            write_json(path,record)
            event(directory,'preregistered',manifest_identity=record['manifest_identity'],measured_jobs_created=0)
            print(record,flush=True)
        finally:
            lock.seek(0); msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)


if __name__ == '__main__': main()
