"""Validate and attach supplemental context review without recoding primary samples.
Safe to rerun against agent checkpoints. No new effective dates enter the timeline.
"""
from pathlib import Path
import json,hashlib,collections,csv,datetime
R=Path(__file__).resolve().parent;O=R.parent;F=O/'full250'
read=lambda p:json.loads(p.read_text('utf8'))
save=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
sha=lambda b:hashlib.sha256(b).hexdigest()
original=read(F/'web_expanded_clauses.json');country_names={r['iso3']:r['country'] for r in read(F/'country_review_audit.json')}
proposals=[];decisions=[]
for folder in sorted(R.glob('parallel_*')):
 for pattern,target in [('*proposed_clauses.json',proposals),('*review_decisions.json',decisions)]:
  for p in sorted(folder.glob(pattern)):
   rows=read(p)
   assert isinstance(rows,list)
   target.extend(dict(x,parallel_partition=folder.name) for x in rows)
for d in decisions:
 if 'review_method' in d:d['review_method']=str(d['review_method']).replace('Human contextual','Assistant contextual').replace('Targeted manual reading','Assistant targeted reading')
accepted=[];excluded=[];seen=set();source_cache={}
for p in proposals:
 identity=p.get('proposal_id',p.get('clause_id'));iso=p['iso3'];raw=p['raw_sha256']
 try:
  assert iso in country_names
  path=Path(p['source_text_file']);text=path.read_text('utf8');text_hash=sha(text.encode())
  supplied_hash=p.get('text_sha256',p.get('source_text_sha256'));assert text_hash==supplied_hash,'Source text hash mismatch'
  assert sha(Path(p['raw_file']).read_bytes())==raw,'Original raw bytes mismatch'
  a=p.get('start_offset',p.get('text_start'));b=p.get('end_offset',p.get('text_end'));quote=p.get('verbatim_extracted_text',p.get('exact_original_text',p.get('verbatim')))
  assert isinstance(a,int) and isinstance(b,int) and 0<=a<b<=len(text)
  assert text[a:b]==quote,'Quotation is not exact source substring'
  key=(iso,raw,a,b)
  if key in seen:continue
  if any(q['iso3']==iso and q['raw_sha256']==raw and q['start_offset'] is not None and q['start_offset']<=a and q['end_offset']>=b for q in original):
   excluded.append(dict(proposal=identity,reason='Passage already wholly contained in the primary reviewed corpus'));continue
  seen.add(key);source_cache[(iso,raw)]=(text,path,p)
  kind=p.get('legal_type',p.get('source_type','Supplemental context'));scope=p.get('scope','See source');status=p.get('operative_status') or p.get('source_provenance_note') or 'Source version and scope retained; no historical recoding'
  interpretation=p.get('research_interpretation',p.get('interpretation',''))
  q=dict(clause_id=f'{iso}-SUP-{raw[:8]}-{a}',iso3=iso,country=country_names[iso],document_id='SUP-'+raw[:20],source_id=p.get('source_id'),source_url=p['source_url'],raw_file=p['raw_file'],raw_sha256=raw,text_sha256=text_hash,source_text_file=str(path.resolve()),start_offset=a,end_offset=b,pdf_page=p.get('pdf_page'),verbatim_extracted_text=quote,display_text=quote,feature_tags=p.get('feature_tags',[]),role=kind,language=p['language'],language_status='Supplemental original-language source; '+str(kind),quote_method=p.get('quote_method','Exact substring of preserved extracted text'),ocr_in_passage=bool(p.get('ocr_in_passage') or 'ocr' in str(kind).lower()),review_status='Context-reviewed supplemental passage; primary comparison unchanged',research_interpretation=f'{kind}. Scope: {scope}. {interpretation}',version_alignment=str(status)+' No new country-year state is inferred from this supplemental review.',evidence_tier='Supplemental: '+str(kind),section_article=p.get('section_article',''),translation_review=None,selected_primary_document=False,supplemental_review=True,source_proposal=identity,parallel_partition=p['parallel_partition'],scope=scope,legal_type=kind,verified_dates=p.get('verified_dates',[]),reported_operative_date=p.get('operative_date',p.get('effective_start')),historical_backfill_permitted=False)
  is_ocr=bool(q['ocr_in_passage'] or 'ocr' in str(path).lower() or 'ocr' in str(p.get('source_extraction_method') or '').lower())
  q['ocr_in_passage']=is_ocr
  if is_ocr:
   q['quote_method']='Exact substring of preserved OCR transcription; original scan controls'
   q['language_status']+='; OCR transcription'
   q['version_alignment']='OCR transcription. '+str(p.get('text_fidelity_note') or 'Original scan controls; source spelling retained.')+' '+q['version_alignment']
  for key in ['source_extraction_method','ocr_validation_status','verified_image_pages','verified_page_images','text_fidelity_note','effective_start_basis']:
   if key in p:q[key]=p[key]
  if p.get('effective_start_basis'):q['version_alignment']+=' '+p['effective_start_basis']
  for item in p.get('verified_page_images',[]):assert sha(Path(item['image_file']).read_bytes())==item['image_sha256'],'Verified image hash mismatch'
  accepted.append(q)
 except (AssertionError,KeyError,UnicodeError,OSError) as err:excluded.append(dict(proposal=identity,reason=str(err) or type(err).__name__))
save(R/'supplemental_reviewed_clauses.json',accepted);save(R/'supplemental_excluded_proposals.json',excluded)
by_country=collections.defaultdict(list)
for q in accepted:by_country[q['iso3']].append(q)
passage_countries=set(by_country)
for file in (O/'countries').glob('*.json'):
 c=read(file);iso=c['country']['iso3'];c['supplemental_reviewed_clauses']=by_country[iso]
 docs={d['document_id']:d for d in c['source_documents']}
 for q in by_country[iso]:
  text,path,p=source_cache[(iso,q['raw_sha256'])]
  docs[q['document_id']]=dict(document_id=q['document_id'],source_id=q['source_id'],title=q['section_article'] or q['legal_type'],source_url=q['source_url'],raw_file=q['raw_file'],raw_sha256=q['raw_sha256'],extracted_text_file=str(path.resolve()),text_sha256=q['text_sha256'],full_extracted_text=text,extraction_method='Preserved extraction; exact quote and byte hash revalidated during supplemental review',attachment_role='Supplemental only; not the selected primary comparison document',access_conditions='Preserved publicly accessible source response; see source provenance',licensing='No additional redistribution licence inferred')
 c['source_documents']=list(docs.values());c['supplemental_document_review']=dict(passages=len(by_country[iso]),primary_sample_unchanged=True,legal_history_unchanged=True,source_hashes=sorted({q['raw_sha256'] for q in by_country[iso]}))
 save(file,c)
# Preserve the source ledger, then overlay actual context-review decisions. Unaddressed
# documents retain their original pending/screened status, rather than being completed.
baseline=R/'pre_parallel_document_review_ledger.json'
if not baseline.exists():save(baseline,read(R/'document_review_ledger.json'))
ledger=read(baseline);initial_candidates={x['raw_sha256'] for x in ledger if x['review_status']=='Screened: possible relevant wording; contextual review remains'};dd={d['raw_sha256']:d for d in decisions};quote_hashes={q['raw_sha256'] for q in accepted};overlaid=0;fully_read_recoverable_text=0;decision_errors=[]
for row in ledger:
 d=dd.get(row['raw_sha256'])
 if not d:continue
 status=str(d.get('status',d.get('review_status','')))
 # Pending/incomplete entries never become completed merely by being assigned.
 if 'pending' in status.lower() or 'screen' in status.lower() and 'context' not in status.lower():continue
 if 'context' not in status.lower() and 'partial' not in status.lower() and 'review' not in status.lower():continue
 path=Path(d.get('source_text_file',''));ranges=d.get('reviewed_ranges',d.get('reviewed_context_ranges',d.get('reviewed_character_ranges',d.get('ranges',[]))))
 try:
  text=path.read_text('utf8');assert sha(text.encode())==d.get('text_sha256',d.get('source_text_sha256'))
  assert ranges and all(isinstance(a,int) and isinstance(b,int) and 0<=a<b<=len(text) for a,b in ranges)
 except (OSError,AssertionError,ValueError,TypeError) as error:
  decision_errors.append(dict(raw_sha256=row['raw_sha256'],reason='Unvalidated context text/ranges: '+str(error)));continue
 if any(a==0 and b==len(text) for a,b in ranges) and 'partial' not in status.lower():fully_read_recoverable_text+=1
 partial='partial' in status.lower();overlaid+=1
 row['review_status']='Partially context-reviewed; further review remains' if partial else ('Context-reviewed supplemental; exact passages extracted' if row['raw_sha256'] in quote_hashes else 'Context-reviewed candidate; no new general operative pathway extracted')
 row['review_reason']=str(d.get('reason',d.get('review_reason','See partition record')))
 row['review_method']='Assistant contextual review of documented sections/ranges; full versus partial retained in supplemental_context_review_decisions.json'
 row['parallel_review_status']=status;row['reviewed_ranges']=ranges;row['reviewed_sections']=d.get('reviewed_sections',d.get('sections_reviewed',[]))
save(R/'document_review_ledger.json',ledger);save(R/'supplemental_context_review_decisions.json',decisions)
save(R/'supplemental_decision_validation_errors.json',decision_errors)
unresolved=[]
for row in ledger:
 status=row['review_status']
 if status.startswith('Partially') or status.startswith('Screened:') and 'off-topic' not in status:
  next_action='Read remaining legal sections; do not infer absence' if status.startswith('Partially') else ('Recover text/OCR or document access' if 'insufficient' in status else 'Expand multilingual search terms and contextually review original document')
  unresolved.append(dict(raw_sha256=row['raw_sha256'],source_ids=row['source_ids'],urls=row['urls'],status=status,review_reason=row['review_reason'],inspected_ranges=row.get('reviewed_ranges',[]),next_action=next_action))
save(R/'resumable_document_review_queue.json',unresolved)
fields=list(dict.fromkeys(k for row in ledger for k in row))
with (R/'document_review_ledger.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in ledger)
summary=dict(checkpoint_client_date='2026-10-18',checkpoint_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),assigned_candidate_documents=len(initial_candidates),additional_negative_screen_documents=len(set(dd)-initial_candidates),context_review_decisions_applied=overlaid,initial_candidates_with_context_review=sum(x['raw_sha256'] in initial_candidates and x.get('parallel_review_status') is not None for x in ledger),scope_resolved_context_documents=sum('Context-reviewed' in x['review_status'] and x.get('parallel_review_status') is not None for x in ledger),full_recoverable_text_readings=fully_read_recoverable_text,partial_context_status_documents=sum(x['review_status'].startswith('Partially') for x in ledger),remaining_possible_wording_candidates=sum(x['review_status']=='Screened: possible relevant wording; contextual review remains' for x in ledger),remaining_document_queue=len(unresolved),additional_exact_passages=len(accepted),additional_passage_countries=len(passage_countries),new_to_primary_review_countries=sorted(passage_countries-{x['iso3'] for x in original}),primary_national_pathway_count=89,primary_sample_and_historical_panel_unchanged=True,excluded_proposals=len(excluded),unvalidated_context_decisions=len(decision_errors),distinct_original_downloads=len(ledger),completed_country_year_queries=3461,note='3461 is completed country-year searches, not remaining documents. Scope/context review is separate from full-text reading; ranges remain in partition records. Supplemental wording includes drafts, limited routes, historical profiles and official explanations; these do not automatically become operative adoption events.')
save(R/'supplemental_review_summary.json',summary)
save(R/'supplemental_validation.json',dict(passed=not excluded and not decision_errors,exact_passages=len(accepted),raw_byte_hash_checks=len(accepted),decoded_text_hash_checks=len(accepted),exact_offset_checks=len(accepted),context_records_with_validated_text_and_ranges=overlaid,excluded_proposals=excluded,context_validation_errors=decision_errors,primary_pathway_denominator_unchanged=True,historical_state_updates=0))
save(R/'supplemental_data_dictionary.json',dict(primary_layer='reviewed_clauses: existing selected comparison documents; national condition sample89, jurisdictions117. No new source automatically replaces an existing selected version.',supplemental_layer='supplemental_reviewed_clauses: additional exact passages admitted after raw-byte, decoded-text and substring-offset validation. Can include operative rules, guidance, mirrored regulations, drafts, historical surveys, limited access and registration baselines.',fields=dict(raw_sha256='SHA256 of the original downloaded file bytes',text_sha256='SHA256 of UTF8-encoded decoded source text with LF newlines; offsets apply to this text',start_offset='Zero-based inclusive character offset in preserved decoded text',end_offset='Zero-based exclusive character offset',legal_type='Source genre/status; guidance and drafts are not silently treated as binding law',scope='Products, procedures or access function discussed',reported_operative_date='Date reported by source, where established; retained as metadata only in this supplemental pass',historical_backfill_permitted='False for all supplemental passages in this pass',selected_primary_document='False; does not add condition counts to the89-source comparison',parallel_review_status='Contextual scope resolution/partial review/pending; does not imply the whole original PDF was read',reviewed_ranges='Actual character ranges inspected; partial documents remain in the resume queue'),translation_policy='Original wording retained. Checked research translations are labelled; no newly recovered unreviewed machine output enters the65-document English model.',counting_notes='The3461figure is completed country-year searches. Downloaded raw byte hashes, reviewed source documents, passages, countries and operative laws are distinct counts. Repeated regional/MoU source across countries is one document, not independent reforms.'))
V=read(R/'review_summary.json');V['screening_status_counts']=dict(collections.Counter(row['review_status'] for row in ledger));V['parallel_review_checkpoint']=summary;save(R/'review_summary.json',V)
print(json.dumps(summary,indent=2))
