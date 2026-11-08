"""Generic loop diagnostics; no behavior-specific detector decides what Codex sees."""
import re
def score(text):
    units=re.findall(r"\b[\w']+\b",text.lower());grams=list(zip(units,units[1:],units[2:],units[3:]))
    repeated=1-len(set(grams))/len(grams) if grams else 0.
    run=bool(re.search(r'\b(\w+)(?:\W+\1){5,}\b',text,re.I))
    char_run=bool(re.search(r'(.)\1{15,}',text))
    loop=run or char_run or (len(units)>=20 and repeated>.35)
    return {'words':len(units),'unique_units':len(set(units)),'fourgram_repetition':float(repeated),
        'repetition':bool(loop),'low_diversity':bool(len(units)>=20 and len(set(units))<=3),
        'scope':'Coarse loop diagnostics only. Short answers, numbers, code and non-English text are not automatically collapse.'}
