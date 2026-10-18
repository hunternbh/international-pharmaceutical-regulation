"""Merge the preserved timeline with the rebuilt wording report; no data recoding.
Run after full250/build_checkpoint_report.py. Produces two self-contained copies
with file links relative to each output location. Original two-panel bytes retained.
"""
from pathlib import Path
import sys,re,json,html,os,hashlib,datetime,subprocess,shutil
HERE=Path(__file__).resolve().parent;O=HERE.parent;ROOT=O.parents[1]
sys.path.insert(0,str(ROOT/'work/vendor'))
from bs4 import BeautifulSoup
TIMELINE=O.parent/'Global_Reliance_Laws_20261017/figures_2000_2025/Reliance_Timeline.html'
SOURCE=HERE/'timeline_source.html';LEGAL=O/'Regulatory_Reliance_Text_Results.html'
read=lambda p:json.loads(p.read_text('utf8'))
esc=lambda x:html.escape(str(x))
DEFS=[
 (0,'None documented','None documented','No dated reliance arrangement is established for this country-year in the panel. Grey combines missing or unresolved history; it is not confirmed legal absence.',3,'#E5E7EB'),
 (1,'Recognition + local checks','Use a foreign approval','Foreign approval supports domestic permission, with local paperwork and checks. Recognition does not necessarily mean automatic permission.',0,'#0072B2'),
 (2,'Abridged assessment','Repeat part of the scientific review','The domestic regulator uses a foreign assessment and reviews the remaining issues. A full dossier may still be required.',0,'#0072B2'),
 (3,'Verification','Check that the foreign approval applies','The regulator checks the prior approval, the documents and whether the medicine is the same as the approved product.',0,'#0072B2'),
 (4,'Combined reliance routes','More than one approval route','Several routes are available, with eligibility depending on the product, foreign approvals and supporting documents.',0,'#0072B2'),
 (5,'WHO collaborative route','Use an assessment shared through WHO','WHO helps share a prior assessment; the domestic authority makes its own authorisation decision.',0,'#0072B2'),
 (6,'Partial evidence reliance','Accept a particular piece of foreign evidence','A rule accepts a specific input, such as clinical evidence or a manufacturing inspection. It does not establish a shortcut for the whole approval.',1,'#009E73'),
 (7,'Enabling framework','Permit reliance in principle','The authority is empowered to use foreign work. The record does not establish a general operational approval shortcut.',2,'#B5A331'),
 (8,'Foreign-review pilot','Test a limited route','A trial permits use of foreign review for a limited period or set of products. It is grouped with frameworks rather than general routes.',2,'#B5A331')
]
GROUPS=['Foreign work used for approval','Specific evidence accepted','Framework or pilot','None documented']
HELP={str(code):dict(label=label,plain=plain,description=desc,group=group,group_name=GROUPS[group],color=color) for code,label,plain,desc,group,color in DEFS}

def scope_css(css,prefix):
 out=[];pos=0
 while pos<len(css):
  start=css.find('{',pos)
  if start<0:break
  pre=css[pos:start].strip();depth=1;i=start+1
  while i<len(css) and depth:
   if css[i]=='{':depth+=1
   elif css[i]=='}':depth-=1
   i+=1
  body=css[start+1:i-1]
  if pre.startswith('@media') or pre.startswith('@supports'):out.append(pre+'{'+scope_css(body,prefix)+'}')
  elif pre.startswith('@'):out.append(pre+'{'+body+'}')
  else:
   selectors=[]
   for sel in pre.split(','):
    sel=sel.strip()
    selectors.append(re.sub(r'^(?:body|:root)(?=$|\s|:)',prefix,sel) if re.match(r'^(?:body|:root)(?=$|\s|:)',sel) else prefix+' '+sel)
   out.append(','.join(selectors)+'{'+body+'}')
  pos=i
 return '\n'.join(out)

def fragment(soup,markup):return BeautifulSoup(markup,'html.parser')

def rebase(soup,source,output):
 for tag in soup.find_all(True):
  for attr in ['href','src']:
   value=tag.get(attr)
   if not value or value.startswith(('#','data:','http:','https:','mailto:','javascript:')):continue
   target=(source.parent/value).resolve()
   tag[attr]=Path(os.path.relpath(target,output.parent)).as_posix()

TEMPLATE_CSS='''.author-byline{display:flex;flex-wrap:wrap;gap:20px 50px;font-size:15px}.author-sources{font-size:12px}.top-findings{max-width:1648px;margin:10px auto 25px;padding:26px 30px;background:#eef3ee;border:1px solid #d7e0d9;border-radius:7px}.top-findings h2{font:700 30px Georgia,serif;margin-top:0}.top-findings .findings-lead{font:22px Georgia,serif}.top-findings li{margin:15px 0;max-width:1200px}.top-findings .small{font-size:13px;color:#516870}.top-findings a{color:#176b64}#legalPanels .clause>summary{cursor:pointer}#legalPanels .clause>summary h3{font-size:17px}#legalPanels #similarityCountry{max-width:100%}#legalPanels .similarity-wording-link{padding:0;margin:0;border:0;background:transparent;text-align:left;color:#176b64;text-decoration:underline;cursor:pointer}body{margin:0;background:#f9faf7;color:#18313b;font:16px/1.6 system-ui,Segoe UI,sans-serif}*{box-sizing:border-box}.combined-header{max-width:1700px;margin:auto;padding:42px 26px 10px}.combined-header h1{font:700 clamp(30px,4vw,50px)/1.14 Georgia,serif;margin:12px 0 20px;max-width:1200px}.combined-header .eyebrow{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#176b64;font-weight:700}.combined-header p{max-width:1150px;color:#516870}.combined-nav{display:flex;flex-wrap:wrap;gap:12px 25px;margin:22px 0}.combined-nav a{color:#176b64;text-decoration:none;border-bottom:1px solid #aac3b8;padding:5px 0}.summary-strip{display:flex;gap:12px;flex-wrap:wrap;font-size:13px}.summary-strip span{padding:7px 12px;border:1px solid #cbdcd3;background:#edf3ee;border-radius:4px}#timelinePanels,#legalPanels{background:transparent;color:#18313b}#timelinePanels .sectionContainer{max-width:1700px;margin:auto;padding:12px 26px 0}#legalPanels .sectionContainer{max-width:1400px;margin:auto;padding:10px 26px 35px}#timelinePanels .panel{border-radius:7px;box-shadow:none;border-color:#d7e0d9}#timelinePanels h2{font-family:Georgia,serif;font-size:28px;line-height:1.2}#timelinePanels .plain-guide{margin:16px 0;background:#f1f6f2;border-radius:5px;padding:12px 16px;font-size:14px}#timelinePanels .guide-table{width:100%;min-width:0;table-layout:auto;font-size:13px;margin-top:12px;border-collapse:collapse}#timelinePanels .guide-table th,#timelinePanels .guide-table td{position:static;width:auto;height:auto;padding:11px;text-align:left;vertical-align:top;white-space:normal;border-bottom:1px solid #d7e0d9;cursor:default}#timelinePanels .guide-table th{background:#e7efe9}#timelinePanels .guide-table .guide-name{min-width:160px;font-weight:650}#timelinePanels .guide-swatch{display:inline-block;width:13px;height:13px;border-radius:2px;margin-right:6px}#timelinePanels .group-heading th{position:static;background:#e7efe9;color:#18313b;font-size:12px;font-weight:700;text-align:left;height:31px;padding:6px 12px;white-space:normal}#timelinePanels select{font:inherit;color:#18313b;background:white;border:1px solid #bdcbd6;border-radius:5px;padding:8px;max-width:100%}#timelinePanels .plain-guide summary{font-size:14px;font-weight:650}#timelinePanels .view-note{font-size:12px;color:#516870;margin:7px 0 14px}#legalPanels #findings{border-top:0;padding-top:15px}#legalPanels h2{font-size:29px}#legalPanels #findings figure{margin-top:14px}#legalPanels #countrySelect{width:min(100%,520px);margin:8px 0 16px;display:block}#legalPanels .context-details{padding:14px 18px;background:#eef3ee;border-radius:5px;font-size:14px;margin-top:20px}#legalPanels .context-details > summary{font-size:16px;font-weight:650}#legalPanels .econ-note{border-left:4px solid #176b64;background:#e7efe9;padding:15px 18px;margin:20px 0}#legalPanels #moreQuotes{display:none!important}#legalPanels .wording-heading{font-family:Georgia,serif;font-size:22px;margin-top:18px}#legalPanels .verbatim{max-height:none}#legalPanels #backlog > details > div.grid{margin-top:15px}@media(max-width:760px){.combined-header{padding:25px 16px 10px}#timelinePanels .sectionContainer,#legalPanels .sectionContainer{padding-left:14px;padding-right:14px}#timelinePanels .guide-table{font-size:12px}#timelinePanels .guide-table .guide-name{min-width:100px}.combined-nav{gap:10px 18px}.summary-strip span{padding:5px 8px}}
'''

TIMELINE_EXTRA_JS=r'''
const HELP=__HELP__,GROUPS=__GROUPS__;
const originalRows=Array.from(document.querySelectorAll('#heatBody tr[data-search]'));
const countriesForRows=new Map();D.cells.forEach(c=>{if(!countriesForRows.has(c.iso3))countriesForRows.set(c.iso3,[]);countriesForRows.get(c.iso3).push(c)});
originalRows.forEach((r,i)=>{const c=D.cells[Number(r.querySelector('td[data-i]').dataset.i)];r.dataset.iso=c.iso3;r.dataset.order=String(i);r.dataset.group=String(HELP[String(countriesForRows.get(c.iso3).find(x=>x.year===2025).category_code)].group)});
function filteredRows(){
 document.querySelectorAll('#heatBody .group-heading').forEach(r=>r.remove());
 const q=$('countrySearch').value.toLowerCase().trim(),dated=$('datedOnly').checked;let n=0,last=null;
 Array.from($('heatBody').querySelectorAll('tr[data-search]')).forEach(r=>{
  const ok=r.dataset.search.includes(q)&&(!dated||r.dataset.dated==='1');r.hidden=!ok;if(!ok)return;n++;
  if($('rowOrder').value==='group'&&last!==r.dataset.group){last=r.dataset.group;const h=document.createElement('tr');h.className='group-heading';h.innerHTML='<th colspan="27">'+esc(GROUPS[Number(last)])+' · based on the recorded 2025 category</th>';$('heatBody').insertBefore(h,r)}
 });$('rowCount').textContent=n+' of 250 countries / areas';
}
function updateHeatView(){
 document.querySelectorAll('#heatBody .group-heading').forEach(r=>r.remove());
 const mode=$('rowOrder').value;
 const sorted=[...originalRows].sort((a,b)=>mode==='alphabetical'?a.dataset.search.localeCompare(b.dataset.search):mode==='group'?(Number(a.dataset.group)-Number(b.dataset.group)||Number(a.dataset.order)-Number(b.dataset.order)):Number(a.dataset.order)-Number(b.dataset.order));
 sorted.forEach(r=>$('heatBody').appendChild(r));
 const grouped=$('colorView').value==='group';
 document.querySelectorAll('#heatBody td[data-i]').forEach(td=>{const c=D.cells[Number(td.dataset.i)],help=HELP[String(c.category_code)];td.style.backgroundColor=grouped?help.color:D.colors[c.category_code];td.title=c.country+', '+c.year+': '+(grouped?help.group_name:help.label)+'. '+help.description+' References: '+(c.label||'unverified history')});
 const items=grouped?GROUPS.map((_,i)=>({label:GROUPS[i],color:Object.values(HELP).find(h=>h.group===i).color})):D.labels.map((label,i)=>({label:i===0?'None documented':label,color:D.colors[i]}));
 $('heatLegend').innerHTML=items.map(x=>'<span><i style="background:'+x.color+'"></i>'+esc(x.label)+'</span>').join('');
 $('heatViewNote').textContent=grouped?'Colours combine related recorded routes into three broad functions, plus None documented. Cell counts and dates are unchanged.':'Colours retain the original nine recorded categories. Cell counts and dates are unchanged.';
 filteredRows();
}
$('rowOrder').addEventListener('change',updateHeatView);$('colorView').addEventListener('change',updateHeatView);
updateHeatView();
'''


def build(output):
 ts=BeautifulSoup(SOURCE.read_text('utf8'),'html.parser');ls=BeautifulSoup(LEGAL.read_text('utf8'),'html.parser');tm=ts.main;lm=ls.main
 data=json.loads(ts.find('script',id='chartData').string);counts=read(O/'full250/review_counts.json')
 timeline_css=scope_css(ts.style.string,'#timelinePanels');legal_css=scope_css(ls.style.string,'#legalPanels')
 tm.find('header',recursive=False).decompose();tm.name='div';tm['class']='sectionContainer'
 panels=tm.find_all('section',recursive=False);panels[0]['id']='timeline';panels[1]['id']='authority-reach'
 panels[0].h2.string='1. When did countries start using foreign regulatory work?'
 panels[0].find('p').string='Each row is a country or area and each column is a year. The colour shows the recorded approval route. The number shows how many foreign regulatory systems or bodies the rule names.'
 legend=panels[0].find('div',class_='legend');legend['id']='heatLegend'
 panels[0].find(id='downloadPanel').string='Download all 250 countries (CSV)'
 controls=panels[0].find('div',class_='controls')
 controls.append(fragment(ts,'<label for="rowOrder">Order countries <select id="rowOrder"><option value="adoption">First recorded rule</option><option value="group">Group by approach in 2025</option><option value="alphabetical">Alphabetical</option></select></label><label for="colorView">Colours <select id="colorView"><option value="detailed">Detailed pathway types</option><option value="group" selected>Three broad groups</option></select></label>'))
 panels[0].find('div',id='heatScroll').insert_before(fragment(ts,'<p id="heatViewNote" class="view-note"></p>'))
 guides=''.join('<tr><td class="guide-name"><i class="guide-swatch" style="background:'+data['colors'][code]+'"></i>'+esc(label)+'</td><td><b>'+esc(plain)+'</b><br>'+esc(desc)+'</td></tr>' for code,label,plain,desc,group,col in DEFS)
 guide='<div class="plain-guide"><h3>How to read the colours</h3><p><b>Blue — Foreign work used for approval:</b> a prior approval or assessment can be used in a domestic authorisation route. The regulator may still check the product, review parts of the science or refuse the application. This group combines recognition, verification, abridged review, multiple routes and WHO collaboration.</p><p><b>Green — Specific evidence accepted:</b> only a particular input, such as a clinical study or inspection, is accepted; a general approval shortcut is not established.</p><p><b>Gold — Framework or pilot:</b> reliance is enabled in principle or tested on a limited basis.</p><p><b>Grey — None documented:</b> this panel has no established dated arrangement for that year. It includes gaps in historical evidence. It does not establish a ban or confirmed absence.</p><p>The three groups describe <b>what foreign work is used for</b>, rather than ranking legal strictness. The Colours menu can restore the detailed categories.</p><details><summary>Detailed terms: recognition, verification, abridged review and other routes</summary><table class="guide-table"><thead><tr><th>Detailed category</th><th>Plain-language meaning</th></tr></thead><tbody>'+guides+'</tbody></table></details><p><b>Numbers inside cells:</b> a number counts named reference systems; <b>n</b> means an open-ended discretionary foreign-authority rule; <b>number + n</b> records both. <b>NS</b> means the list is not fully specified. <b>†</b> flags a later/current reference list assigned to an earlier year under the historical convention. Click a cell for its sources and dates.</p></div>'
 panels[0].find('div',id='heatScroll').insert_after(fragment(ts,guide))
 panels[1].h2.string='2. Whose regulatory work is accepted abroad?'
 panels[1].find('p').string='Each line represents one of the 58 named national regulatory systems or regional/global bodies. A value of 20 means that 20 destination countries or areas can use that authority’s work in at least one recorded route. A destination may accept more than one authority.'
 ls.header.decompose();lm.name='div';lm['class']='sectionContainer'
 sections={x.get('id'):x for x in lm.find_all('section',recursive=False)}
 for section in sections.values():section.extract()
 findings=sections['findings'];findings.h2.string='3. What conditions do the written rules mention?'
 fig=findings.find('figure');fig.extract();findings.h2.insert_after(fig)
 fig.insert_before(fragment(ls,'<p>Counts use 89 selected national pathways.</p>'))
 fig.find('figcaption').string='A condition may apply only to certain products or routes. A condition not mentioned in the selected passage remains unverified. Statutes, regulations and official guidance are identified separately in the country viewer.'
 fig.insert_after(fragment(ls,'<p class="econ-note"><b>Why this matters economically.</b> Reusing a foreign review can save repeated scientific work. The firm may still have to obtain review reports, show that it is selling the same medicine, and answer local questions. These remaining steps are potential costs of market entry.</p>'))
 complexity=sections['complexity'];complexity.h2.string='Which countries write similar rules?'
 from similarity_panel import panel as similarity_panel
 similarity_markup,similarity_js=similarity_panel(O)
 for child in list(complexity.contents):
  if child is not complexity.h2:child.extract()
 complexity.append(fragment(ls,similarity_markup))
 wording=sections['wording'];wording.h2.string='4. Country wording'
 p=wording.find('p');p.string='Choose a country, then click a passage heading to expand its exact wording, explanation and source links. Passages start collapsed. The initial country is the United Kingdom.'
 published=sections['published'];published.h2.string='How does this compare with published research?'
 backlog=sections['backlog'];backlog.h2.string='What the latest document review added'
 for h in list(backlog.find_all('h3')):
  if h.get_text() in ['Reliance also runs between emerging markets','Written time savings can be measured directly']:h.parent.decompose()
 bd=ls.new_tag('details');bd['class']='context-details';bs=ls.new_tag('summary');bs.string='Review expansion, added countries and concrete examples';bd.append(bs)
 for child in list(backlog.contents):
  if child is not backlog.h2:bd.append(child.extract())
 backlog.append(bd)
 sections['methods'].h2.string='5. What is complete, and what resumes next?'
 for key in ['findings','complexity','wording','published','backlog','audit','methods']:lm.append(sections[key])
 # Preserve every completion/resumption paragraph exactly apart from relative URLs.
 rebase(ls,LEGAL,output)
 timeline_js=ts.find_all('script')[-1].string
 timeline_js=timeline_js.replace("function filteredRows(){", "function originalFilteredRows(){",1).replace("addEventListener('input',filteredRows)","addEventListener('input',()=>filteredRows())").replace("addEventListener('change',filteredRows)","addEventListener('change',()=>filteredRows())")
 timeline_js=timeline_js.replace("if(c.category_code){h+=", "h+='<p class=\"plain-guide\">'+esc(HELP[String(c.category_code)].description)+'</p>';if(c.category_code){h+=",1)
 timeline_js=timeline_js.replace("$('detailContent').innerHTML=h;$('detailDialog').showModal()}", "h+='<p><button id=\"openCountryWording\">Read this country’s exact wording</button></p>';$('detailContent').innerHTML=h;$('detailDialog').showModal();$('openCountryWording').addEventListener('click',()=>{$('detailDialog').close();window.dispatchEvent(new CustomEvent('reliance-country',{detail:{iso3:c.iso3}}));document.getElementById('wording').scrollIntoView({behavior:'smooth'})})}",1)
 extra=TIMELINE_EXTRA_JS.replace('__HELP__',json.dumps(HELP,ensure_ascii=False)).replace('__GROUPS__',json.dumps(GROUPS,ensure_ascii=False))
 # Add grouping definitions before first execution; function declarations are hoisted.
 timeline_js=timeline_js.replace("'use strict';", "'use strict';\nconst HELP="+json.dumps(HELP,ensure_ascii=False)+",GROUPS="+json.dumps(GROUPS,ensure_ascii=False)+";",1)
 extra=re.sub(r'^\s*const HELP=.*?;\n','',extra,count=1)
 timeline_js+=extra
 legal_js=ls.find_all('script')[-1].string
 relative=Path(os.path.relpath(O,output.parent)).as_posix();base='' if relative=='.' else relative+'/'
 legal_js=legal_js.replace('href="countries/','href="'+base+'countries/')
 legal_js+=similarity_js
 legal_js+="\nwindow.addEventListener('reliance-country',event=>{const iso=event.detail.iso3;if(countries.some(c=>c[0]===iso)){$('countrySelect').value=iso;$('quoteSearch').value='';renderClauses();}});"
 for script in ts.find_all('script'):script.extract()
 for script in ls.find_all('script'):script.extract()
 # Keep the source JSON payload untouched for data-integrity comparison.
 chart_json=BeautifulSoup(SOURCE.read_text('utf8'),'html.parser').find('script',id='chartData')
 main_timeline=''.join(str(x) for x in ts.body.contents)
 main_legal=''.join(str(x) for x in ls.body.contents)
 header=f'''<header class="combined-header"><div class="eyebrow">International pharmaceutical regulation</div><h1>Foreign Drug Approval Reliance Laws</h1><div class="author-byline"><p><b>Hunter Ng</b> · Baruch College, CUNY<br><a href="mailto:hunterboonhian.ng@baruch.cuny.edu">hunterboonhian.ng@baruch.cuny.edu</a></p><p><b>Shou-Ming Chang</b> · The Graduate Center, CUNY<br><a href="mailto:schang@gradcenter.cuny.edu">schang@gradcenter.cuny.edu</a></p></div><div class="summary-strip"><span>250 countries and areas</span><span>Timeline: 2000–2025</span><span>{counts['national_authorisation_texts']} selected national approval pathways</span><span>{counts['jurisdictions_individually_reviewed']} jurisdiction text reviews</span></div><nav class="combined-nav"><a href="#main-findings">Main findings</a><a href="#timeline">1. Country timelines</a><a href="#authority-reach">2. Reference-authority reach</a><a href="#findings">3. Written conditions</a><a href="#wording">4. Country wording</a><a href="#methods">5. Completion and next steps</a></nav></header>'''
 top_findings="""<section id="main-findings" class="top-findings"><h2>Main findings</h2><p class="findings-lead">Countries import regulatory knowledge while retaining control over market entry.</p><ol><li><b>Reliance changes the work required for entry.</b> 58% of national pathways address foreign assessment reports, 45% address product or dossier sameness, and 34% address additional local evidence or assessment. The rules connect reuse of scientific work to information and product requirements. <a href="#findings">See the wording counts</a>.</li><li><b>National discretion survives international integration.</b> 56% of national pathways retain domestic decision, refusal or further-review powers. Reliance therefore creates a form of integration in which a country can use another regulator’s assessment while preserving its own decision. <a href="#wording">Read the country clauses</a>.</li><li><b>Regional legal families are a major source of common wording.</b> Shared European procedures appear together in the recognition-oriented wording theme. The country comparisons reveal both common regional language and similarities across regions. <a href="#complexity">Explore the text comparison</a>.</li></ol><p class="small">Counts use 89 selected national pathways.</p></section>"""
 std_path=O.parent/'Regulatory_Reliance_Standard_Drug_20261018/panel.html'
 standard_panel=std_path.read_text('utf8') if std_path.exists() else ''
 if standard_panel:
  rr=read(O.parent/'Regulatory_Reliance_Standard_Drug_20261018/analysis_results.json');nn=rr['adjudicated_legal_comparisons']['complete_report_gate']['n']
  std_download=Path(os.path.relpath(O/'standard_drug',output.parent)).as_posix()
  standard_panel=standard_panel.replace('</section>',f'<p><a href="{std_download}/analysis_results.json">Download results JSON</a> · <a href="{std_download}/all_250_country_comparison.json">Country comparisons JSON</a> · <a href="{std_download}/reproduce_counts.py">Reproduce the counts</a> · <a href="{std_download}/research_questions.json">Economics questions JSON</a></p></section>',1)
  top_findings=top_findings.replace('<ol>',f'<ol><li><b>For the same drug, access to the underlying review can determine the available shortcut.</b> We establish a complete-assessment-report condition in {nn} selected route options. Public approval summaries do not meet that condition; other eligibility requirements and alternative routes remain separate. <a href="#standardDrugPanel">See the fixed-drug comparison</a>.</li>',1)
 if standard_panel:
  header=header.replace('<a href="#wording">','<a href="#standardDrugPanel">Same-drug comparison</a><a href="#wording">')
  # Preserve the established panel order. Add the new comparison after the
  # wording/similarity analysis, before the country passage viewer.
  main_legal=main_legal.replace('<section id="wording">',standard_panel+'<section id="wording">',1)
 document='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Foreign Drug Approval Reliance Laws</title><meta name="author" content="Hunter Ng; Shou-Ming Chang"><style>'+timeline_css+'\n'+legal_css+'\n'+TEMPLATE_CSS+'</style></head><body>'+header+'<main id="combinedMain">'+top_findings+'<div id="timelinePanels">'+main_timeline+'</div><div id="legalPanels">'+main_legal+'</div></main>'+str(chart_json)+'<script>(()=>{'+timeline_js+'})();</script><script>(()=>{'+legal_js+'})();</script></body></html>'
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(document,encoding='utf8')
 return dict(file=str(output),bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest())

subprocess.run([sys.executable,str(HERE/'build_translated_comparison.py')],check=True,stdout=subprocess.DEVNULL)
STD=O.parent/'Regulatory_Reliance_Standard_Drug_20261018'
if (STD/'analysis_results.json').exists():
 (O/'standard_drug').mkdir(exist_ok=True)
 for name in ['analysis_results.json','all_250_country_comparison.json','primary_country_comparison.json','comparison_adjudication.json','research_questions.json','case_definition.json','european_family.json','reproduce_counts.py']:
  shutil.copyfile(STD/name,O/'standard_drug'/name)
outputs=[build(TIMELINE),build(O/'International_Pharmaceutical_Regulation.html')]
manifest=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),outputs=outputs,timeline_source=str(SOURCE),timeline_source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),wording_source=str(LEGAL),wording_source_sha256=hashlib.sha256(LEGAL.read_bytes()).hexdigest(),groups=HELP,data_policy='Display-only regrouping. No dates, categories, counts, links or legal coding changed.',panel_order=['Main findings','Country-year heatmap','Reference-authority reach','Descending condition counts','Text comparison','Standardized-drug legal comparison','Single-country exact wording','Published research','Review additions','Country audit','What is complete, and what resumes next?'])
(HERE/'combined_report_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(outputs,indent=2))
