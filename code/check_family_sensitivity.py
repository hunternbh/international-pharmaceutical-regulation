"""Separate legal families and document genres; never treat duplicated institutions as policy replications."""
from pathlib import Path
import sys,json,re,collections
F=Path(__file__).resolve().parent;O=F.parent;ROOT=O.parents[1];sys.path.insert(0,str(ROOT/'work/vendor'))
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer,CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import adjusted_rand_score
from sklearn.decomposition import LatentDirichletAllocation
from nltk.stem.snowball import EnglishStemmer
def read(p):return json.loads(p.read_text('utf8'))
R=read(F/'analysis/text_analysis_results.json');docs=read(F/'analysis/model_documents.json');M=read(F/'web_expanded_country_documents.json');Q=read(F/'web_expanded_clauses.json');mm={m['iso3']:m for m in M}
eu={m['iso3'] for m in M if m.get('shared_procedure_family')=='EU/EEA shared authorisation' or m['iso3'] in {'MLT','NLD','ESP','LIE','PRT','HUN'}}
regional=eu|{m['iso3'] for m in M if m['family'].startswith('EAEU')} 
definitions=read(O/'expanded_review/expanded_feature_definitions.json');features=[]
for sample,ids in [('All selected authorisation texts',{m['iso3'] for m in M if m['primary_legal_comparison']}),('Excluding EU/EEA and bilateral European shared-system texts',{m['iso3'] for m in M if m['primary_legal_comparison'] and m['iso3'] not in eu})]:
 for key,label in definitions.items():
  positive=[iso for iso in sorted(ids) if any(key in q['feature_tags'] for q in Q if q['iso3']==iso and q['document_id']==mm[iso]['document_id'])]
  features.append(dict(sample=sample,feature=key,label=label,count=len(positive),denominator=len(ids),countries=positive))
stops=set(R['methods']['domain_stopwords']);names=set(R['methods']['names_removed']);stem=EnglishStemmer()
def tokens(t):return [stem.stem(w) for w in re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?",t.lower()) if len(w)>2 and w not in stops and w not in names]
dd=[d for d in docs if d['iso3'] not in eu];C=CountVectorizer(analyzer=tokens,min_df=2,max_df=.95).fit_transform([d['analysis_text'] for d in dd]);base=LatentDirichletAllocation(n_components=2,max_iter=100,random_state=20261017,n_jobs=1).fit(C).transform(C).argmax(1);ari=[]
for seed in range(10):
 alt=LatentDirichletAllocation(n_components=2,max_iter=80,random_state=seed,n_jobs=1).fit(C).transform(C).argmax(1);ari.append(float(adjusted_rand_score(base,alt)))
primary={m['iso3'] for m in M if m['primary_legal_comparison']};core=['reports','unredacted','sameness','local_evidence','approval_age','two_approvals','foreign_marketing','manufacture_location','scope_limit','applicant_consent','translation_requirement']
complexity=[]
for iso in sorted(primary):
 tags={tag for q in Q if q['iso3']==iso and q['document_id']==mm[iso]['document_id'] for tag in q['feature_tags']}
 complexity.append(dict(iso3=iso,documented_requirement_dimensions=sum(k in tags for k in core),dimensions=[k for k in core if k in tags],interpretation='Number of expressly coded dimensions in selected passages. This is not a statutory burden, legal length, compliance cost or absence score.'))
result=dict(family_feature_sensitivity=features,english_without_new_shared_family_n=len(dd),two_topic_seed_ari_excluding_new_family=ari,two_topic_median_ari_excluding_new_family=float(np.median(ari)),two_topic_median_ari_all=R['topics']['median_adjusted_rand_index'],excluded_european_family_countries=sorted(eu),excluded_eaeu_family_countries=sorted(regional-eu),interpretation='European shared-authorisation vocabulary can form a cluster. All identified European shared systems are excluded in the sensitivity, including earlier reviewed countries. Two topics are exploratory and are not universally validated regulatory regimes.',requirement_dimension_counts=complexity,requirement_dimension_median=float(np.median([r['documented_requirement_dimensions'] for r in complexity])),requirement_dimension_iqr=np.quantile([r['documented_requirement_dimensions'] for r in complexity],[.25,.75]).tolist(),wording_model_scope='Selected source versions; clauses and genres differ in length. No price, review-time or access effect is estimated here.')
(F/'analysis/family_sensitivity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in result.items() if k not in ['family_feature_sensitivity','requirement_dimension_counts']},indent=2))
