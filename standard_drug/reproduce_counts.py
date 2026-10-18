"""Reproduce the legal comparison's counts using only Python's standard library.

Usage: python reproduce_counts.py --input-dir PATH
The directory contains primary_country_comparison.json, analysis_results.json,
comparison_adjudication.json and european_family.json. This reproduces counts
from contextual coding; it does not automate interpretation of legislation.
"""
from pathlib import Path
import argparse, json, collections, hashlib

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input-dir',default=str(Path(__file__).resolve().parent));args=ap.parse_args()
    d=Path(args.input_dir);read=lambda n:json.loads((d/n).read_text(encoding='utf8'))
    p=read('primary_country_comparison.json')['records'];r=read('analysis_results.json');a=read('comparison_adjudication.json')
    assert len(p)==89 and len({x['iso3'] for x in p})==89
    sets={k:set(v) for k,v in a['country_sets'].items()}
    components=[]
    for c in r['components']:
        counts=dict(collections.Counter(x['components'][c['component']]['state'] for x in p))
        assert counts==c['counts'],c['component']
        components.append({'component':c['component'],'counts':counts})
    case={k:dict(collections.Counter(x['cases'][k]['status'] for x in p)) for k in 'ABCDE'}
    assert case==r['case_status_counts']
    for k,s in sets.items():assert len(s)==r['adjudicated_legal_comparisons'][k]['n']
    eu=set(read('european_family.json')['countries'])
    sensitivity=[]
    for label,sub in [('All selected national pathways',p),('Excluding identified European shared-system family',[x for x in p if x['iso3'] not in eu]),('Official English source',[x for x in p if x['language']=='en']),('Original non-English sources',[x for x in p if x['language']!='en'])]:
        ids={x['iso3'] for x in sub};sensitivity.append({'sample':label,'n':len(sub),**{k:len(ids&s) for k,s in sets.items()}})
    assert sensitivity==r['sensitivity']
    result={'passed':True,'primary_records':len(p),'component_counts':components,'case_counts':case,'adjudicated_counts':{k:len(s) for k,s in sets.items()},'sensitivity':sensitivity,'input_sha256':{n:hashlib.sha256((d/n).read_bytes()).hexdigest() for n in ['primary_country_comparison.json','comparison_adjudication.json']},'note':'Reproduced descriptive counts, not causal effects or independent legal recoding.'}
    (d/'counts_reproduced.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'passed':True,'countries':len(p),'components':len(components),'cases':5,'sensitivity_samples':4},indent=2))

if __name__=='__main__':main()
