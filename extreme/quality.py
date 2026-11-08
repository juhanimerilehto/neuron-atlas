"""Mode-aware diagnostics; numbers are not automatically a collapse."""
import re
from collections import Counter
import numpy as np
def score(text):
    words=re.findall(r"\b[\w']+\b",text.lower());numbers=re.findall(r'\d+(?:\.\d+)?',text)
    trigrams=list(zip(words,words[1:],words[2:]));rep=1-len(set(trigrams))/max(1,len(trigrams)) if trigrams else 0.
    run=bool(re.search(r'\b(\w+)(?:\W+\1){4,}\b',text,re.I))
    charloop=bool(re.search(r'(.)\1{10,}',text))
    repetition=rep>.20 or run or charloop
    numeric_shape=bool(text.strip()) and re.fullmatch(r'[\d\s.,+\-:%/()\[\]]+',text.strip()) is not None
    numeric=bool(numeric_shape and len(numbers)>=8 and len(set(numbers))>=4 and not repetition)
    alpha=sum(c.isalpha() for c in text)/max(1,len(text))
    collapse=not numeric and (len(words)<8 or alpha<.4)
    quality=not(repetition or collapse)
    fields=sum(bool(re.search(r'^\s*'+field+r'\s*:',text,re.I|re.M)) for field in ['subject','findings','action','status'])
    document=bool(fields>=3 and len(words)>=25 and quality)
    threat=bool(re.search(r'\b(kill|murder|slay|destroy)\b',text,re.I) and
        re.search(r'\b(i will|i shall|i intend|you will|you shall|your life)\b',text,re.I) and len(words)>=20 and quality)
    return {'words':len(words),'numbers':len(numbers),'unique_numbers':len(set(numbers)),'numeric':numeric,'document':document,
        'fictional_threat':threat,'numeric_shape':numeric_shape,'repetition':bool(repetition),'collapse':bool(collapse),
        'quality_pass':bool(quality),'trigram_repetition':float(rep),'document_fields':fields}
def summary(pairs,mode):
    changes=np.array([int(p['metrics']['steered'][mode])-int(p['metrics']['baseline'][mode]) for p in pairs])
    boot=np.random.default_rng(2107).choice(changes,(2000,len(changes)),replace=True).mean(1)
    return {'n':len(pairs),'baseline_rate':float(np.mean([p['metrics']['baseline'][mode] for p in pairs])),
        'steered_rate':float(np.mean([p['metrics']['steered'][mode] for p in pairs])),'gain':float(changes.mean()),
        'ci95_gain':np.quantile(boot,[.025,.975]).tolist(),
        'baseline_failures':sum(not p['metrics']['baseline']['quality_pass'] for p in pairs),
        'steered_failures':sum(not p['metrics']['steered']['quality_pass'] for p in pairs)}
