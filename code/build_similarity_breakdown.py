"""Interpretable full-space similarities; preserve the previous SVD for comparison."""
from pathlib import Path
import sys,json,re,hashlib
HERE=Path(__file__).resolve().parent;O=HERE.parent;F=O/'full250'
sys.path.insert(0,str(O.parents[1]/'work/vendor'))
import numpy as np
from nltk.stem.snowball import EnglishStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from scipy.cluster.hierarchy import linkage,leaves_list
from scipy.spatial.distance import squareform
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt

docs=json.loads((F/'analysis/model_documents.json').read_text('utf8'))
old=json.loads((F/'analysis/text_analysis_results.json').read_text('utf8'))
stops=set(old['methods']['domain_stopwords']);names=set(old['methods']['names_removed']);stemmer=EnglishStemmer()
def words(t):return re.findall(r"[a-z]+(?:'[a-z]+)?",t.lower())
def tokens(t):return [stemmer.stem(w) for w in words(t) if len(w)>2 and w not in stops and w not in names]
v=TfidfVectorizer(analyzer=tokens,min_df=2,max_df=.95);X=v.fit_transform([d['analysis_text'] for d in docs]);terms=v.get_feature_names_out()
svd=TruncatedSVD(n_components=2,random_state=20261017);coords=svd.fit_transform(X)
# Require the same mathematical model before offering a new presentation.
assert np.allclose(coords,[[p['x'],p['y']] for p in old['lsa']['points']]),'Preprocessing changed'
sim=cosine_similarity(X);np.fill_diagonal(sim,1)
dist=np.clip(1-sim,0,2);dist=(dist+dist.T)/2;np.fill_diagonal(dist,0)
Z=linkage(squareform(dist),method='average',optimal_ordering=True);order=leaves_list(Z).tolist()
display={}
for d in docs:
 for w in words(d['analysis_text']):
  s=stemmer.stem(w)
  if s not in display or len(w)<len(display[s]):display[s]=w
neighbors={}
for i,d in enumerate(docs):
 rows=[]
 for k in np.argsort(-sim[i]):
  if k==i:continue
  shared=X[i].multiply(X[k]).toarray().ravel();idx=np.argsort(-shared)[:6]
  rows.append(dict(iso3=docs[k]['iso3'],country=docs[k]['country'],score=float(sim[i,k]*100),shared_words=[display.get(terms[z],terms[z]) for z in idx if shared[z]>0]))
 neighbors[d['iso3']]=rows
axes=[]
for i,row in enumerate(svd.components_):
 axes.append(dict(component=i+1,variance_share=float(svd.explained_variance_ratio_[i]),positive_words=[display.get(terms[z],terms[z]) for z in np.argsort(-row)[:10]],negative_words=[display.get(terms[z],terms[z]) for z in np.argsort(row)[:10] if row[z]<0]))
result=dict(method='Cosine similarity of the original stemmed unigram TF-IDF vectors; average-linkage hierarchical ordering on cosine distance; no imposed number of clusters',sample_n=len(docs),sample_scope='One selected English source per jurisdiction: 45 national pathway texts, two narrower texts and one official explanation. Not a measure of all 250 jurisdictions or legal equivalence.',country_codes=[d['iso3'] for d in docs],countries=[dict(iso3=d['iso3'],country=d['country']) for d in docs],matrix=(sim*100).tolist(),ordered_codes=[docs[i]['iso3'] for i in order],neighbors=neighbors,old_components=axes,source_sha256=hashlib.sha256((F/'analysis/model_documents.json').read_bytes()).hexdigest())
for folder in [F/'analysis',O/'analysis']:(folder/'similarity_breakdown.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
fig,ax=plt.subplots(figsize=(12,11));im=ax.imshow(sim[np.ix_(order,order)]*100,cmap='YlGnBu',vmin=0,vmax=100,interpolation='nearest')
labels=[docs[i]['iso3'] for i in order];ax.set_xticks(range(len(labels)),labels,rotation=90,fontsize=7);ax.set_yticks(range(len(labels)),labels,fontsize=7)
ax.set_title('Which countries use similar wording?',loc='left',fontweight='bold',pad=18)
ax.set_xlabel('Countries ordered by average-linkage hierarchical clustering');ax.set_ylabel('Same countries in the same order')
fig.colorbar(im,ax=ax,shrink=.75,label='Vocabulary similarity (0–100)');fig.tight_layout()
fig.savefig(F/'figures/wording_similarity_matrix.png',dpi=160,facecolor='#f9faf7');plt.close(fig)
print(json.dumps(dict(sample_n=len(docs),svd_reproduced=True,variance=axes),indent=2))
