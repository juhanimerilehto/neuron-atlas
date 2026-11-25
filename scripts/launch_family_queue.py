"""Detach the finite authorized queue, retaining resumable jobs and separate process logs."""
from datetime import datetime, timezone
import json
import ctypes
import os
from pathlib import Path
import subprocess
import sys


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

ROOT = Path(__file__).resolve().parents[1]
state = ROOT / '.cache/family-queue-service.json'
if state.exists() and alive(json.loads(state.read_text())['pid']):
    raise RuntimeError('Family queue already running')
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
log = ROOT / '.cache' / (stamp + '-family-queue.log')
with log.open('ab') as stream:
    process = subprocess.Popen([sys.executable, str(ROOT / 'scripts/run_family_queue.py')], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUNBUFFERED': '1'},
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_BREAKAWAY_FROM_JOB)
value = {'pid': process.pid, 'log': log.relative_to(ROOT).as_posix(),
         'started_utc': datetime.now(timezone.utc).isoformat(), 'queue': ['paired-lfm25-350m-v1', 'granite40-350m-v1']}
state.write_text(json.dumps(value, indent=2) + '\n')
print(json.dumps(value), flush=True)
