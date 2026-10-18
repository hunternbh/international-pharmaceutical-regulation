"""Reproducible descriptive legal-text analysis. Run after curate_clauses.py."""
from pathlib import Path
import sys,json,re,collections,itertools,math
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/vendor'))
import numpy as np,pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer,CountVectorizer,ENGLISH_STOP_WORDS
from sklearn.decomposition import TruncatedSVD,LatentDirichletAllocation
from sklearn.metrics import adjusted_rand_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import KFold
from nltk.stem.snowball import EnglishStemmer
import cmudict,pyphen
E=Path(__file__).resolve().parent;O=E.parent;A=E/'analysis';A.mkdir(exist_ok=True)
if '--web-expanded' in sys.argv:
 A=O/'full250/analysis';A.mkdir(exist_ok=True)
 Q=json.loads((O/'full250/web_expanded_clauses.json').read_text('utf8'))
 M=json.loads((O/'full250/web_expanded_country_documents.json').read_text('utf8'))
else:
 Q=json.loads((E/'expanded_clauses.json').read_text('utf8'))
 M=json.loads((E/'expanded_country_documents.json').read_text('utf8'))
F=json.loads((E/'expanded_feature_definitions.json').read_text('utf8'))
countries=pd.read_csv(O/'analysis/country_archive_coverage.csv').set_index('iso3')['country'].to_dict()
TR={r['id']:r for r in json.loads((E/'checked_translations.json').read_text('utf8'))}
stemmer=EnglishStemmer();cmu=cmudict.dict();hyph=pyphen.Pyphen(lang='en_US')
easy_path=ROOT/'work/vendor/textstat/resources/en/easy_words.txt'
if not easy_path.exists():
 import textstat
 easy_path=Path(textstat.__file__).parent/'resources/en/easy_words.txt'
easy=set(easy_path.read_text('utf8').lower().split())

def clean(t):
 t=re.sub(r'(?m)^PAGE \d+\s*$',' ',t)
 t=re.sub(r'(?m)^\s*\d{1,3}\s*$',' ',t) # PDF margin line/page numbers
 t=re.sub(r'\[MACHINE OCR;[^\]]*\]',' ',t)
 t=re.sub(r'https?://\S+',' ',t)
 return re.sub(r'\s+',' ',t).strip()

def merge_passages(m):
 # Primary model uses the selected document only, not all national/context files.
 rows=[q for q in Q if q['iso3']==m['iso3'] and q['document_id']==m['document_id'] and q['start_offset'] is not None]
 ranges=sorted((q['start_offset'],q['end_offset']) for q in rows);merged=[]
 for a,b in ranges:
  if merged and a<=merged[-1][1]:merged[-1][1]=max(b,merged[-1][1])
  else:merged.append([a,b])
 if not rows:return ''
 p=Path(rows[0]['source_text_file'])
 if p.exists():t=p.read_text('utf8')
 else:
  archive=json.loads((O/'countries'/f"{m['iso3']}.json").read_text('utf8'))
  t=next(s['full_extracted_text'] for s in archive['source_documents'] if s['document_id']==m['document_id'])
 return clean('\n'.join(t[a:b] for a,b in merged))

def words(t):return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?",t.lower())
def syll(w):
 if w in cmu:return min(sum(c[-1:].isdigit() for c in p) for p in cmu[w]) or 1
 return max(1,len(hyph.inserted(w).split('-')))
def readability(t):
 w=words(t);n=len(w);s=max(1,len([x for x in re.split(r'[.!?]+\s+(?=[A-Z])',t) if len(words(x))>=3]));sy=[syll(x) for x in w]
 asl=n/s;spw=sum(sy)/max(n,1);hard=sum(x not in easy for x in w)/max(n,1)*100
 return dict(words=n,sentences=s,words_per_sentence=asl,syllables_per_word=spw,flesch_kincaid=0.39*asl+11.8*spw-15.59,gunning_fog=0.4*(asl+100*sum(x>=3 for x in sy)/max(n,1)),dale_chall=0.1579*hard+0.0496*asl+(3.6365 if hard>5 else 0),oov_syllable_share=sum(x not in cmu for x in w)/max(n,1))

docs=[];feature_rows=[]
for m in M:
 qs=[q for q in Q if q['iso3']==m['iso3'] and q['document_id']==m['document_id']];tags=set(itertools.chain.from_iterable(q['feature_tags'] for q in qs))
 feature_rows.append(dict(iso3=m['iso3'],country=countries[m['iso3']],evidence_tier=m['evidence_tier'],primary_legal_comparison=m['primary_legal_comparison'],primary_english=m['primary_english_sample'],**{k:int(k in tags) for k in F}))
 if m['primary_english_sample']:
  t=merge_passages(m)
  if len(words(t))<80:continue
  docs.append(dict(**m,country=countries[m['iso3']],analysis_text=t,**readability(t)))
pd.DataFrame(feature_rows).to_csv(A/'country_feature_presence.csv',index=False)
pd.DataFrame([{k:v for k,v in d.items() if k not in ['analysis_text','clause_ids']} for d in docs]).to_csv(A/'english_document_metrics.csv',index=False)
(A/'model_documents.json').write_text(json.dumps(docs,ensure_ascii=False,indent=2),encoding='utf8')

# Preserve negation and legal modals; domain stopwords remove repeated genre labels.
stops=set(ENGLISH_STOP_WORDS)-{'no','not','nor','may','must','shall','should','will','cannot','without'}
stops|={'regulatory','regulation','authority','authorities','medicine','medicines','medicinal','pharmaceutical','pharmaceuticals','product','products','page','guideline','guidelines','application','applications','section','annex','figure','table','document','documents','shall','http','www'}
stops.discard('shall')
names=set()
for d in docs:names|=set(words(d['country']))
names|={'mhra','sahpra','hsa','sfda','npra','nafdac','tmda','efda','rwanda','ghana','gambia','swissmedic','malawi','kenya','pakistan','lanka','singapore','tanzania','ethiopia','nigeria','malaysia','egypt','saudi','arabia','tuvalu','tonga','jersey','micronesia','georgia','zealand','drap','fda','ema','tga','pmda','chmp','european','australia','australian','canada','canadian','japan','japanese','swiss','switzerland','united','kingdom','states'}
def tokens(t,strip_names=True):
 return [stemmer.stem(w) for w in words(t) if len(w)>2 and w not in stops and (not strip_names or w not in names)]
texts=[d['analysis_text'] for d in docs];labels=[d['iso3'] for d in docs]
tf=TfidfVectorizer(analyzer=lambda t:tokens(t),min_df=2,max_df=.95)
X=tf.fit_transform(texts);terms=tf.get_feature_names_out()
svd=TruncatedSVD(n_components=2,random_state=20261017);coords=svd.fit_transform(X)
sim=cosine_similarity(X);pairs=sorted([dict(a=labels[i],b=labels[j],similarity=float(sim[i,j])) for i in range(len(docs)) for j in range(i+1,len(docs))],key=lambda r:-r['similarity'])
topterms=[dict(term=terms[i],mean_tfidf=float(np.asarray(X.mean(axis=0)).ravel()[i])) for i in np.argsort(np.asarray(X.mean(axis=0)).ravel())[-25:][::-1]]

# Document-held-out perplexity is exploratory: a small selected corpus, not an optimal universal taxonomy.
cv=CountVectorizer(analyzer=lambda t:tokens(t),min_df=2,max_df=.95)
C=cv.fit_transform(texts);cterms=cv.get_feature_names_out();folds=list(KFold(3,shuffle=True,random_state=20261017).split(texts))
cvres=[]
for k in [2,3,4]:
 scores=[]
 for train,test in folds:
  model=LatentDirichletAllocation(n_components=k,max_iter=60,learning_method='batch',random_state=20261017,n_jobs=1)
  model.fit(C[train]);scores.append(float(model.perplexity(C[test])))
 cvres.append(dict(topics=k,mean_heldout_perplexity=float(np.mean(scores)),fold_perplexities=scores))
best=min(cvres,key=lambda x:x['mean_heldout_perplexity'])['topics']
lda=LatentDirichletAllocation(n_components=best,max_iter=100,random_state=20261017,n_jobs=1).fit(C);theta=lda.transform(C)
stability=[]
for seed in range(10):
 alt=LatentDirichletAllocation(n_components=best,max_iter=80,random_state=seed,n_jobs=1).fit(C)
 stability.append(dict(seed=seed,adjusted_rand_index=float(adjusted_rand_score(theta.argmax(1),alt.transform(C).argmax(1)))))
topicwords=[dict(topic=i+1,terms=[cterms[j] for j in np.argsort(row)[-12:][::-1]]) for i,row in enumerate(lda.components_)]

# Text preprocessing sensitivity; similarity correlation and nearest-neighbour retention.
rawtf=TfidfVectorizer(analyzer=lambda t:tokens(t,False),min_df=2,max_df=.95)
rawsim=cosine_similarity(rawtf.fit_transform(texts));tri=np.triu_indices(len(docs),1)
np.fill_diagonal(sim,-1);np.fill_diagonal(rawsim,-1)
sens=dict(pair_similarity_correlation_with_agency_names=float(np.corrcoef(sim[tri],rawsim[tri])[0,1]),nearest_neighbour_retention=float(np.mean(sim.argmax(1)==rawsim.argmax(1))))
# Separate original-English and guideline-only subsets; no translations or genres silently pooled.
subset=[]
for name,ds in [('all_selected_English',docs),('excluding_official_translation',[d for d in docs if 'translation' not in d['language_status'].lower()]),('guidelines_only',[d for d in docs if d['genre']=='Guideline'])]:
 subset.append(dict(sample=name,n=len(ds),median_words_per_sentence=float(np.median([d['words_per_sentence'] for d in ds])),median_fk=float(np.median([d['flesch_kincaid'] for d in ds])),median_fog=float(np.median([d['gunning_fog'] for d in ds])),median_dale_chall=float(np.median([d['dale_chall'] for d in ds]))))
feature_summary=[]
for k,title in F.items():
 hit=[d['iso3'] for d in docs if any(k in q['feature_tags'] for q in Q if q['iso3']==d['iso3'] and q['document_id']==d['document_id'])]
 feature_summary.append(dict(feature=k,label=title,count=len(hit),denominator=len(docs),countries=hit))
pd.DataFrame(feature_summary).to_csv(A/'feature_summary_primary.csv',index=False)
pd.DataFrame(pairs).to_csv(A/'text_similarity_pairs.csv',index=False)
pd.DataFrame(stability).to_csv(A/'topic_seed_sensitivity.csv',index=False)
pd.DataFrame(subset).to_csv(A/'readability_sensitivity.csv',index=False)
result=dict(nlp_n=len(docs),reviewed_jurisdictions=len(M),reviewed_clauses=len(Q),features=feature_summary,top_terms=topterms,lsa=dict(explained_variance=svd.explained_variance_ratio_.tolist(),points=[dict(iso3=d['iso3'],country=d['country'],x=float(coords[i,0]),y=float(coords[i,1]),topic=int(theta[i].argmax()+1),topic_shares=theta[i].tolist(),genre=d['genre'],words=d['words'],fk=d['flesch_kincaid'],wps=d['words_per_sentence']) for i,d in enumerate(docs)]),similar_pairs=pairs[:15],topics=dict(selected_k=best,heldout=cvres,top_words=topicwords,seed_stability=stability,median_adjusted_rand_index=float(np.median([r['adjusted_rand_index'] for r in stability]))),preprocessing_sensitivity=sens,readability_sensitivity=subset,methods=dict(random_seed=20261017,unit='One selected source document per reviewed English jurisdiction; overlapping passage offsets merged',stemming='NLTK English Snowball; no POS tagging or claimed lemmatisation',negations_and_modals_retained=['no','not','nor','may','must','shall','should','cannot','without'],domain_stopwords=sorted(stops),names_removed=sorted(names),tfidf='Stemmed unigrams, min_df=2; each jurisdiction has equal document weight',lsa='Two-component truncated SVD; first component can reflect general vocabulary, not a causal axis',lda='Bag-of-stem counts; k=2,3,4, 3-fold document-held-out perplexity; fixed corpus vocabulary (exploratory selection, not an independent validation set); 10-seed ARI sensitivity',readability='Rule-based sentence splitting; CMU syllables with Pyphen fallback; Dale-Chall bundled easy-word list. Fog counts all >=3-syllable words without proper-noun/compound exceptions. Approximate formula scores, not literal schooling years.',feature_counting='Expressly present in reviewed passages; not observed is not legal absence; reviewed passages can include supporting annex sources outside the primary NLP document',scope='Selected English clauses, not all 250 countries; current texts are not retroactively assigned to historical years'))
(A/'text_analysis_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(n=len(docs),k=best,readability=subset,stability=result['topics']['median_adjusted_rand_index'],sensitivity=sens,features=[(f['feature'],f['count']) for f in feature_summary]),indent=2))

# All-language source coding: one selected national document per jurisdiction.
legal=[r for r in feature_rows if r['primary_legal_comparison']]
all_features=[dict(feature=k,label=title,count=sum(r[k] for r in legal),denominator=len(legal),countries=[r['iso3'] for r in legal if r[k]]) for k,title in F.items()]
result['all_language_legal_features']=all_features
result['legal_n']=len(legal)
result['tier_counts']=dict(collections.Counter(m['evidence_tier'] for m in M))
result['methods']['feature_counting']='Express wording in each jurisdiction’s selected primary document only. Supporting or historical documents are displayed separately and cannot add contemporaneous features. No observed feature is not proof of legal absence. Selected versions vary in date; this is not a 2026 legal census.'

# Translation sensitivity requires EVERY selected passage from the primary document
# to have a checked rendering. Never use the quarantined raw machine output.
extra=[];excluded=[]
for m in M:
 if m['language']=='en' or not m['primary_legal_comparison']:continue
 qs=[q for q in Q if q['iso3']==m['iso3'] and q['document_id']==m['document_id']]
 if not qs or not all(TR.get(q['clause_id'],{}).get('approved_for_text_sensitivity') for q in qs):
  excluded.append(dict(iso3=m['iso3'],reason='Not every selected passage has an approved checked research translation'));continue
 text=clean(' '.join(TR[q['clause_id']]['checked_translation'] for q in sorted(qs,key=lambda q:q.get('start_offset') or 0)))
 if len(words(text))<80:
  excluded.append(dict(iso3=m['iso3'],reason='Fewer than 80 English words; original and checked translation remain available for reading'));continue
 extra.append(dict(iso3=m['iso3'],country=countries[m['iso3']],analysis_text=text,translation='Checked and corrected local-Argos research rendering; readability excluded'))
combined=docs+extra;ct=[d['analysis_text'] for d in combined]
v=TfidfVectorizer(analyzer=lambda t:tokens(t),min_df=2,max_df=.95);Y=v.fit_transform(ct);ss=cosine_similarity(Y)
cc=CountVectorizer(analyzer=lambda t:tokens(t),min_df=2,max_df=.95).fit_transform(ct)
translation_stability=[]
for k in [2,3,4]:
 a=LatentDirichletAllocation(n_components=k,max_iter=80,random_state=20261017,n_jobs=1).fit(cc).transform(cc).argmax(1)
 scores=[]
 for seed in range(5):
  b=LatentDirichletAllocation(n_components=k,max_iter=60,random_state=seed,n_jobs=1).fit(cc).transform(cc).argmax(1)
  scores.append(float(adjusted_rand_score(a,b)))
 translation_stability.append(dict(k=k,median_ari=float(np.median(scores)),seed_ari=scores))
idx=np.triu_indices(len(docs),1)
translation_sensitivity=dict(n=len(combined),original_English_n=len(docs),additional_checked_translation_n=len(extra),additional_countries=[d['iso3'] for d in extra],english_pair_similarity_correlation=float(np.corrcoef(cosine_similarity(X)[idx],ss[:len(docs),:len(docs)][idx])[0,1]),topic_seed_checks=translation_stability,excluded=excluded,scope='Separate mixed-language sensitivity; no translated readability or unchecked machine output. Shared-system pages remain correlated: see legal-family sensitivity.')
result['translation_sensitivity']=translation_sensitivity
(A/'translation_sensitivity_documents.json').write_text(json.dumps(combined,ensure_ascii=False,indent=2),encoding='utf8')
(A/'all_language_feature_summary.json').write_text(json.dumps(all_features,ensure_ascii=False,indent=2),encoding='utf8')
(A/'text_analysis_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(legal_n=len(legal),tier_counts=result['tier_counts'],translation_sensitivity=translation_sensitivity),indent=2))
