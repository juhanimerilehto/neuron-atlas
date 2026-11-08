"""Download only data files from a pinned Qwen checkpoint."""
import json
from pathlib import Path
from huggingface_hub import snapshot_download
root=Path(__file__).resolve().parents[1]
revision='70d244cc86ccca08cf5af4e1e306ecf908b1ad5e'
snapshot=snapshot_download('Qwen/Qwen3-1.7B',revision=revision,cache_dir=str(root/'.cache/hub-qwen'),
    allow_patterns=['*.json','*.safetensors','*.txt','*.model','README.md'],max_workers=2)
out=root/'campaigns/extreme-qwen-pilot-v2';out.mkdir(parents=True,exist_ok=True)
value={'repository':'Qwen/Qwen3-1.7B','revision':revision,'snapshot':snapshot}
(out/'model.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({'repository':value['repository'],'revision':revision,'download_complete':True}),flush=True)
