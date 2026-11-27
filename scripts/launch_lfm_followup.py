"""Detach a versioned finite follow-up process with Windows duplicate-process protection."""
import argparse
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def alive(pid):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_bool, ctypes.c_uint32]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x100000, False, pid)
    if not handle:
        return False
    try:
        return kernel.WaitForSingleObject(handle, 0) == 0x102
    finally:
        kernel.CloseHandle(handle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('module', choices=['confirmation_v1', 'programme_v1'], nargs='?', default='confirmation_v1')
    args = parser.parse_args()
    state = ROOT / '.cache/lfm-followup-service.json'
    if state.exists() and alive(json.loads(state.read_text(encoding='utf-8'))['pid']):
        raise RuntimeError('LFM follow-up already running')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    log = ROOT / '.cache' / (stamp + '-lfm-followup.log')
    with log.open('ab') as stream:
        process = subprocess.Popen([sys.executable, str(ROOT / 'scripts/run_lfm_followup.py'), args.module],
            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUNBUFFERED': '1'},
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_BREAKAWAY_FROM_JOB)
    value = {'pid': process.pid, 'module': args.module, 'log': log.relative_to(ROOT).as_posix(),
             'started_utc': datetime.now(timezone.utc).isoformat(), 'programme': 'lfm-depth-20261127-v1'}
    state.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(value), flush=True)


if __name__ == '__main__':
    main()
