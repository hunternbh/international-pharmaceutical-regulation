"""Paper-style legal-text comparison using English and checked translations equally.
Unit: one selected primary document per jurisdiction; never add unreviewed machine output.
No new historical legal dates or feature codings are inferred by this model.
"""
from pathlib import Path
import sys,json,re,hashlib,collections
HERE=Path(__file__).resolve().parent;O=HERE.parent;ROOT=O.parents[1];F=O/'full250';A=F/'analysis'
sys.path.insert(0,str(ROOT/'work/vendor'))
import numpy as np,nltk
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer,CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import adjusted_rand_score
from sklearn.decomposition import LatentDirichletAllocation
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cmudict,pyphen
read=lambda p:json.loads(p.read_text('utf8'))
old=read(A/'text_analysis_results.json');base=read(A/'model_documents.json');M=read(F/'web_expanded_country_documents.json');Q=read(F/'web_expanded_clauses.json');TR={r['id']:r for r in read(O/'expanded_review/checked_translations.json')}
names={r['iso3']:r['country'] for r in read(F/'country_review_audit.json')}
def words(t):return re.findall(r"[a-z]+(?:'[a-z]+)?",t.lower())
def clean(t):return re.sub(r'\s+',' ',re.sub(r'https?://\S+',' ',t)).strip()
def original(m,qs):
 ranges=[]
 for q in sorted(qs,key=lambda q:q['start_offset'] or 0):
  if q['start_offset'] is None:return clean(' '.join(q['verbatim_extracted_text'] or q['display_text'] for q in qs))
  a,b=q['start_offset'],q['end_offset']
  if ranges and a<=ranges[-1][1]:ranges[-1][1]=max(b,ranges[-1][1])
  else:ranges.append([a,b])
 c=read(O/'countries'/f'{m["iso3"]}.json');text=next(d['full_extracted_text'] for d in c['source_documents'] if d['document_id']==m['document_id'])
 return clean(' '.join(text[a:b] for a,b in ranges))
docs=[dict(d,analysis_language_basis='Official English text',checked_translation=False,short_excerpt=d['words']<80) for d in base];present={d['iso3'] for d in docs};excluded=[]
for m in M:
 if m['iso3'] in present:continue
 qs=[q for q in Q if q['iso3']==m['iso3'] and q['document_id']==m['document_id']]
 if not qs:continue
 if m['primary_english_sample']:
  text=original(m,qs);basis='Official English text';translated=False
 elif m['language']!='en' and all(TR.get(q['clause_id'],{}).get('approved_for_text_sensitivity') and TR[q['clause_id']].get('checked_translation') for q in qs):
  text=clean(' '.join(TR[q['clause_id']]['checked_translation'] for q in sorted(qs,key=lambda q:q['start_offset'] or 0)));basis='Checked research translation treated as English analysis text';translated=True
 else:
  if m['language']!='en':excluded.append(dict(iso3=m['iso3'],reason='Not every selected primary-document passage has a checked translation; originals retained'))
  continue
 if len(words(text))<10:excluded.append(dict(iso3=m['iso3'],reason='Fewer than ten English words'));continue
 docs.append(dict(**m,country=names[m['iso3']],analysis_text=text,words=len(words(text)),analysis_language_basis=basis,checked_translation=translated,short_excerpt=len(words(text))<80,source_clause_ids=[q['clause_id'] for q in qs]));present.add(m['iso3'])
assert len(present)==len(docs)
for d in docs:
 d['analysis_text_sha256']=hashlib.sha256(d['analysis_text'].encode()).hexdigest()
 d.setdefault('source_clause_ids',d.get('clause_ids',[]))
# Match the paper's POS-aware lemmatisation. Retain legal modals/negations as an explicit adaptation.
resource_dir=ROOT/'work/nltk_data';resource_dir.mkdir(exist_ok=True);nltk.data.path.insert(0,str(resource_dir))
for item,path in [('averaged_perceptron_tagger_eng','taggers/averaged_perceptron_tagger_eng'),('wordnet','corpora/wordnet.zip')]:
 try:nltk.data.find(path)
 except LookupError:assert nltk.download(item,download_dir=str(resource_dir),quiet=True)
stops=set(old['methods']['domain_stopwords']);excluded_names=set(old['methods']['names_removed'])
for d in docs:excluded_names.update(words(d['country']))
lem=WordNetLemmatizer();posmap={'J':'a','N':'n','V':'v','R':'r'};legal={'no','not','nor','may','must','shall','should','cannot','without','will'}
spelling={'authorisation':'authorization','authorise':'authorize','recognise':'recognize','recognition':'recognition','centralised':'centralized','decentralised':'decentralized','organisation':'organization','labelling':'labeling','programme':'program','licence':'license'}
def tokenise(text):
 out=[]
 for w,tag in nltk.pos_tag(words(text)):
  if len(w)<=2 or w in stops or w in excluded_names:continue
  if tag[:1] not in posmap and w not in legal:continue
  word=lem.lemmatize(w,posmap.get(tag[:1],'n'));out.append(spelling.get(word,word))
 return out
token_docs=[tokenise(d['analysis_text']) for d in docs]
tf=TfidfVectorizer(analyzer=lambda x:x,min_df=2,max_df=.95);X=tf.fit_transform(token_docs);terms=tf.get_feature_names_out();sim=cosine_similarity(X)
assert np.all(np.diag(sim)>.999999)
neighbors={}
for i,d in enumerate(docs):
 rows=[]
 for k in np.argsort(-sim[i]):
  if i==k:continue
  shared=X[i].multiply(X[k]).toarray().ravel();indices=np.argsort(-shared)[:6]
  rows.append(dict(iso3=docs[k]['iso3'],country=docs[k]['country'],score=float(np.clip(sim[i,k]*100,0,100)),shared_words=[str(terms[z]) for z in indices if shared[z]>0],checked_translation=docs[k]['checked_translation'],short_excerpt=docs[k]['short_excerpt']))
 neighbors[d['iso3']]=rows
counts=CountVectorizer(analyzer=lambda x:x,min_df=2,max_df=.95);Y=counts.fit_transform(token_docs);vocab=counts.get_feature_names_out();binary=(Y>0).astype(int)
order=np.argsort(-np.asarray(binary.sum(axis=0)).ravel())[:14]
frequencies=[dict(term=str(vocab[i]),count=int(binary[:,i].sum()),percent=float(binary[:,i].sum()/len(docs)*100)) for i in order]
# The paper chooses topic count by coherence on a random 75% sample. We specify UMass
# coherence explicitly; vocabulary is fitted on that training sample, then the selected
# topic count is refitted on the full sample. Candidate k=2..5; fixed 20261017 seed.
rng=np.random.default_rng(20261017);train_idx=np.sort(rng.choice(len(docs),int(.75*len(docs)),replace=False));train=[token_docs[i] for i in train_idx]
cv=CountVectorizer(analyzer=lambda x:x,min_df=2,max_df=.95);T=cv.fit_transform(train);B=(T>0).astype(int).toarray()
def coherence(model,binary):
 scores=[]
 for row in model.components_:
  idx=np.argsort(-row)[:10]
  for a in range(1,len(idx)):
   for b in range(a):scores.append(np.log(((binary[:,idx[a]]*binary[:,idx[b]]).sum()+1)/max(binary[:,idx[b]].sum(),1)))
 return float(np.mean(scores))
candidates=[]
for k in range(2,6):
 model=LatentDirichletAllocation(n_components=k,max_iter=80,random_state=20261017,n_jobs=1).fit(T)
 candidates.append(dict(k=k,training_umass_coherence=coherence(model,B)))
best=max(candidates,key=lambda r:r['training_umass_coherence'])['k'];model=LatentDirichletAllocation(n_components=best,max_iter=80,random_state=20261017,n_jobs=1).fit(Y);theta=model.transform(Y);dominant=theta.argmax(axis=1)
stability=[]
for seed in range(10):
 alt=LatentDirichletAllocation(n_components=best,max_iter=80,random_state=seed,n_jobs=1).fit_transform(Y).argmax(axis=1);stability.append(float(adjusted_rand_score(dominant,alt)))
topics=[]
for k,row in enumerate(model.components_):
 members=[d['iso3'] for i,d in enumerate(docs) if dominant[i]==k]
 topics.append(dict(topic=k+1,keywords=[str(vocab[i]) for i in np.argsort(-row)[:10]],count=len(members),percent=len(members)/len(docs)*100,countries=members,mean_topic_share=float(theta[:,k].mean())))
for i,d in enumerate(docs):d.update(topic=int(dominant[i]+1),topic_shares=theta[i].tolist(),retained_token_count=len(token_docs[i]))
cmu=cmudict.dict();hyph=pyphen.Pyphen(lang='en_US');easy=set((ROOT/'work/vendor/textstat/resources/en/easy_words.txt').read_text('utf8').lower().split())
def readability(text):
 w=words(text);n=len(w);s=max(1,len([x for x in re.split(r'[.!?]+\s+(?=[A-Z])',text) if len(words(x))>=3]))
 syll=[min(sum(p[-1:].isdigit() for p in pronunciation) for pronunciation in cmu[t]) or 1 if t in cmu else max(1,len(hyph.inserted(t).split('-'))) for t in w]
 asl=n/s;spw=sum(syll)/max(n,1);hard=sum(t not in easy for t in w)/max(n,1)*100
 return dict(words_per_sentence=asl,flesch_kincaid=.39*asl+11.8*spw-15.59,gunning_fog=.4*(asl+100*sum(v>=3 for v in syll)/max(n,1)),dale_chall=.1579*hard+.0496*asl+(3.6365 if hard>5 else 0))
for d in docs:d['english_surface_readability']=readability(d['analysis_text'])
readability_summary=[]
for label,rows in [('All English analysis texts',docs),('Official English sources',[d for d in docs if not d['checked_translation']]),('Checked translations',[d for d in docs if d['checked_translation']])]:
 readability_summary.append(dict(sample=label,n=len(rows),**{k:float(np.median([d['english_surface_readability'][k] for d in rows])) for k in ['words_per_sentence','flesch_kincaid','gunning_fog','dale_chall']}))
# Sensitivities: remove translated texts and remove short excerpts, using the same
# full-fit topics for composition, and refit vectors for nearest-match sensitivity.
checks=[]
for name,idx in [('Official English only',[i for i,d in enumerate(docs) if not d['checked_translation']]),('At least 80 English words',[i for i,d in enumerate(docs) if not d['short_excerpt']])]:
 z=TfidfVectorizer(analyzer=lambda x:x,min_df=2,max_df=.95).fit_transform([token_docs[i] for i in idx]);s=cosine_similarity(z);tri=np.triu_indices(len(idx),1)
 checks.append(dict(sample=name,n=len(idx),pairwise_similarity_correlation=float(np.corrcoef(sim[np.ix_(idx,idx)][tri],s[tri])[0,1]),dominant_topic_counts=[int(sum(dominant[i]==k for i in idx)) for k in range(best)]))
result=dict(method='POS-aware WordNet lemmatisation; content words plus legal modals/negation; TF-IDF cosine similarity. LDA topics chosen by UMass coherence on a fixed 75% training sample, k=2..5, refitted on all texts.',sample_n=len(docs),official_english_n=sum(not d['checked_translation'] for d in docs),checked_translation_n=sum(d['checked_translation'] for d in docs),translated_countries=[d['iso3'] for d in docs if d['checked_translation']],short_excerpt_n=sum(d['short_excerpt'] for d in docs),primary_n=sum(d['primary_legal_comparison'] for d in docs),country_codes=[d['iso3'] for d in docs],countries=[{k:d[k] for k in ['iso3','country','checked_translation','short_excerpt','words','evidence_tier']} for d in docs],matrix=(sim*100).tolist(),neighbors=neighbors,word_frequencies=frequencies,topics=topics,topic_selection=candidates,selected_topics=best,topic_seed_ari=stability,topic_median_ari=float(np.median(stability)),sensitivities=checks,readability_summary=readability_summary,excluded=excluded,translation_policy='Checked translations are the de facto English texts with the same weighting as official English texts. All selected primary passages must be checked. No 80-word exclusion in the main comparison; short excerpts are flagged and tested separately.',adaptation='Follows Gurrola-Perez and Lin (2024), Section 5: POS/lemmatisation, word importance, LDA keywords and jurisdiction counts. Their source texts use official English translations; ours additionally use checked research translations. UMass coherence, seed tests and nearest matches are explicit extensions; not a replication.',scope='One selected primary source per jurisdiction; pathway, limited-scope and explanatory texts separately identified. Translated readability is not evidence about original-language drafting complexity.')
for folder in [A,O/'analysis']:
 (folder/'similarity_breakdown.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
 (folder/'combined_english_analysis_documents.json').write_text(json.dumps(docs,ensure_ascii=False,indent=2),encoding='utf8')
fig,ax=plt.subplots(figsize=(10.5,5.6));ax.barh(range(len(frequencies)),[r['percent'] for r in frequencies],color='#176b64');ax.set_yticks(range(len(frequencies)),[r['term'] for r in frequencies]);ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xlabel(f'Percentage of the {len(docs)} selected English or translated texts using the word');ax.spines[['top','right']].set_visible(False)
for i,row in enumerate(frequencies):ax.text(row['percent']+1,i,f'{row["percent"]:.0f}%',va='center')
fig.tight_layout();fig.savefig(F/'figures/word_frequency_ranking.png',dpi=160,facecolor='#f9faf7');plt.close(fig)
print(json.dumps({k:result[k] for k in ['sample_n','official_english_n','checked_translation_n','translated_countries','short_excerpt_n','primary_n','selected_topics','topic_median_ari','topics','sensitivities']},indent=2))
