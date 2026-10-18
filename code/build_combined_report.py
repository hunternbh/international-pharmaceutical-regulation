"""Merge the preserved timeline with the rebuilt wording report; no data recoding.
Run after full250/build_checkpoint_report.py. Produces two self-contained copies
with file links relative to each output location. Original two-panel bytes retained.
"""
from pathlib import Path
import sys,re,json,html,os,hashlib,datetime
HERE=Path(__file__).resolve().parent;O=HERE.parent;ROOT=O.parents[1]
sys.path.insert(0,str(ROOT/'work/vendor'))
from bs4 import BeautifulSoup
TIMELINE=O.parent/'Global_Reliance_Laws_20261017/figures_2000_2025/Reliance_Timeline.html'
SOURCE=HERE/'timeline_source.html';LEGAL=O/'Regulatory_Reliance_Text_Results.html'
read=lambda p:json.loads(p.read_text('utf8'))
esc=lambda x:html.escape(str(x))
DEFS=[
 (0,'Unknown / unverified','History not established','We have not established a dated rule for this country and year. Grey is a gap in the record; it does not mean the country prohibited reliance.',6,'#E5E7EB'),
 (1,'Recognition + local checks','Use an existing foreign approval','An earlier foreign approval can support domestic permission to sell the medicine. The applicant still completes the local documents and any required checks.',0,'#0072B2'),
 (2,'Abridged assessment','Repeat only part of the scientific review','The regulator uses work already done abroad and concentrates its assessment on the remaining issues. A full application dossier can still be required.',1,'#009E73'),
 (3,'Verification','Check that the foreign approval applies','The regulator checks that this is the same medicine and that the foreign approval, documents and product meet the route’s conditions.',0,'#0072B2'),
 (4,'Combined reliance routes','Several routes are available','The country offers more than one kind of reliance route. The route used can depend on the medicine, its earlier approvals and the documents available.',2,'#8064A2'),
 (5,'WHO collaborative route','Share an assessment through WHO','WHO coordinates access to an assessment by WHO or a trusted regulator. The domestic authority uses that material to make its own decision.',3,'#56B4E9'),
 (6,'Partial evidence reliance','Accept only part of the foreign evidence','The rule accepts a particular input, such as foreign clinical evidence or a manufacturing inspection. The cell does not establish a shortcut for the whole approval process.',4,'#CC79A7'),
 (7,'Enabling framework','Allow reliance in principle','A law or policy gives the authority power to use foreign work. Detailed eligibility and application procedures may be specified in separate rules.',5,'#8C7853'),
 (8,'Foreign-review pilot','Test a foreign-review route','A trial or pilot permits use of foreign assessment work for a defined period or set of products. It is kept separate from a general permanent route.',5,'#8C7853')
]
GROUPS=['Use an existing foreign approval','Repeat only part of the scientific review','Several routes are available','Share an assessment through WHO','Accept only part of the foreign evidence','Frameworks and pilots','History not established']
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

TEMPLATE_CSS='''body{margin:0;background:#f9faf7;color:#18313b;font:16px/1.6 system-ui,Segoe UI,sans-serif}*{box-sizing:border-box}.combined-header{max-width:1700px;margin:auto;padding:42px 26px 10px}.combined-header h1{font:700 clamp(30px,4vw,50px)/1.14 Georgia,serif;margin:12px 0 20px;max-width:1200px}.combined-header .eyebrow{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#176b64;font-weight:700}.combined-header p{max-width:1150px;color:#516870}.combined-nav{display:flex;flex-wrap:wrap;gap:12px 25px;margin:22px 0}.combined-nav a{color:#176b64;text-decoration:none;border-bottom:1px solid #aac3b8;padding:5px 0}.summary-strip{display:flex;gap:12px;flex-wrap:wrap;font-size:13px}.summary-strip span{padding:7px 12px;border:1px solid #cbdcd3;background:#edf3ee;border-radius:4px}#timelinePanels,#legalPanels{background:transparent;color:#18313b}#timelinePanels .sectionContainer{max-width:1700px;margin:auto;padding:12px 26px 0}#legalPanels .sectionContainer{max-width:1400px;margin:auto;padding:10px 26px 35px}#timelinePanels .panel{border-radius:7px;box-shadow:none;border-color:#d7e0d9}#timelinePanels h2{font-family:Georgia,serif;font-size:28px;line-height:1.2}#timelinePanels .plain-guide{margin:16px 0;background:#f1f6f2;border-radius:5px;padding:12px 16px;font-size:14px}#timelinePanels .guide-table{width:100%;min-width:0;table-layout:auto;font-size:13px;margin-top:12px;border-collapse:collapse}#timelinePanels .guide-table th,#timelinePanels .guide-table td{position:static;width:auto;height:auto;padding:11px;text-align:left;vertical-align:top;white-space:normal;border-bottom:1px solid #d7e0d9;cursor:default}#timelinePanels .guide-table th{background:#e7efe9}#timelinePanels .guide-table .guide-name{min-width:160px;font-weight:650}#timelinePanels .guide-swatch{display:inline-block;width:13px;height:13px;border-radius:2px;margin-right:6px}#timelinePanels .group-heading th{position:static;background:#e7efe9;color:#18313b;font-size:12px;font-weight:700;text-align:left;height:31px;padding:6px 12px;white-space:normal}#timelinePanels select{font:inherit;color:#18313b;background:white;border:1px solid #bdcbd6;border-radius:5px;padding:8px;max-width:100%}#timelinePanels .plain-guide summary{font-size:14px;font-weight:650}#timelinePanels .view-note{font-size:12px;color:#516870;margin:7px 0 14px}#legalPanels #findings{border-top:0;padding-top:15px}#legalPanels h2{font-size:29px}#legalPanels #findings figure{margin-top:14px}#legalPanels #countrySelect{width:min(100%,520px);margin:8px 0 16px;display:block}#legalPanels .context-details{padding:14px 18px;background:#eef3ee;border-radius:5px;font-size:14px;margin-top:20px}#legalPanels .context-details > summary{font-size:16px;font-weight:650}#legalPanels .econ-note{border-left:4px solid #176b64;background:#e7efe9;padding:15px 18px;margin:20px 0}#legalPanels #moreQuotes{display:none!important}#legalPanels .wording-heading{font-family:Georgia,serif;font-size:22px;margin-top:18px}#legalPanels .verbatim{max-height:none}#legalPanels #backlog > details > div.grid{margin-top:15px}@media(max-width:760px){.combined-header{padding:25px 16px 10px}#timelinePanels .sectionContainer,#legalPanels .sectionContainer{padding-left:14px;padding-right:14px}#timelinePanels .guide-table{font-size:12px}#timelinePanels .guide-table .guide-name{min-width:100px}.combined-nav{gap:10px 18px}.summary-strip span{padding:5px 8px}}
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
 const items=grouped?[0,2,4,5,6,7,1].map((_,i)=>({label:GROUPS[i],color:Object.values(HELP).find(h=>h.group===i).color})):D.labels.map((label,i)=>({label,color:D.colors[i]}));
 $('heatLegend').innerHTML=items.map(x=>'<span><i style="background:'+x.color+'"></i>'+esc(x.label)+'</span>').join('');
 $('heatViewNote').textContent=grouped?'Colours combine related recorded routes into six broad approaches, plus unknown history. Cell counts and dates are unchanged.':'Colours retain the original nine recorded categories. Cell counts and dates are unchanged.';
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
 controls.append(fragment(ts,'<label for="rowOrder">Order countries <select id="rowOrder"><option value="adoption">First recorded rule</option><option value="group">Group by approach in 2025</option><option value="alphabetical">Alphabetical</option></select></label><label for="colorView">Colours <select id="colorView"><option value="detailed">Original pathway types</option><option value="group">Broader economic groups</option></select></label>'))
 panels[0].find('div',id='heatScroll').insert_before(fragment(ts,'<p id="heatViewNote" class="view-note"></p>'))
 guides=''.join('<tr><td class="guide-name"><i class="guide-swatch" style="background:'+data['colors'][code]+'"></i>'+esc(label)+'</td><td><b>'+esc(plain)+'</b><br>'+esc(desc)+'</td></tr>' for code,label,plain,desc,group,col in DEFS)
 guide='<details class="plain-guide"><summary>What does each colour mean? Plain-language guide</summary><p>Reliance means using another authority’s work to support a domestic decision. The main economic distinction is how much scientific review is repeated locally, and what documents the firm still has to provide.</p><table class="guide-table"><thead><tr><th>Recorded category</th><th>What the firm and regulator do</th></tr></thead><tbody>'+guides+'</tbody></table><p><b>Broader groups:</b> recognition and verification are grouped as using an existing foreign approval; enabling frameworks and pilots are grouped as frameworks and trials. Abridged review, multiple routes, WHO collaboration and partial-evidence rules remain separate. Grouping changes the display, not the underlying legal record.</p><p><b>Reading the cell:</b> a number counts named reference systems; <b>n</b> indicates a discretionary rule open to any foreign authority; <b>number + n</b> records both. <b>NS</b> means the list is not fully specified. <b>†</b> flags a later/current list assigned to earlier years; other qualifiers remain explained in the cell’s source notes.</p></details>'
 panels[0].find('div',id='heatScroll').insert_after(fragment(ts,guide))
 panels[1].h2.string='2. Whose regulatory work is accepted abroad?'
 panels[1].find('p').string='Each line represents one of the 58 named national regulatory systems or regional/global bodies. A value of 20 means that 20 destination countries or areas can use that authority’s work in at least one recorded route. A destination may accept more than one authority.'
 ls.header.decompose();lm.name='div';lm['class']='sectionContainer'
 sections={x.get('id'):x for x in lm.find_all('section',recursive=False)}
 for section in sections.values():section.extract()
 findings=sections['findings'];findings.h2.string='3. What conditions do the written rules mention?'
 fig=findings.find('figure');fig.extract();findings.h2.insert_after(fig)
 fig.insert_before(fragment(ls,f'<p>These counts use one selected national approval-pathway text for each of {counts["national_authorisation_texts"]} countries or areas. Bars run from most common to least common. The counts describe wording found in those texts.</p>'))
 fig.find('figcaption').string='A condition may apply only to certain products or routes. A condition not mentioned in the selected passage remains unverified. Statutes, regulations and official guidance are identified separately in the country viewer.'
 fig.insert_after(fragment(ls,'<p class="econ-note"><b>Why this matters economically.</b> Reusing a foreign review can save repeated scientific work. The firm may still have to obtain review reports, show that it is selling the same medicine, and answer local questions. These remaining steps are potential costs of market entry.</p>'))
 complexity=sections['complexity'];complexity.h2.string='How similar are the rules, and how many conditions do they describe?'
 complexity.find('p').string='The wording often returns to three issues: access to the foreign assessment, whether the medicine is the same, and what the domestic regulator still checks. Shared regional procedures can also produce similar wording across several countries.'
 card=complexity.find('div',class_='card');details=ls.new_tag('details');details['class']='context-details';summary=ls.new_tag('summary');summary.string='Text-analysis details and checks';details.append(summary)
 for child in list(card.contents):details.append(child.extract())
 result=read(O/'full250/analysis/text_analysis_results.json');family=read(O/'full250/analysis/family_sensitivity.json')
 card.append(fragment(ls,f'<h3>A transparent grouping is easier to interpret</h3><p>The heatmap’s grouping menu combines routes according to how they use foreign work. The median reviewed text explicitly mentions {family["requirement_dimension_median"]:.0f} of the 11 requirement dimensions we track. That is a count of documented conditions, rather than an estimate of monetary cost.</p><p>Automated text clustering does not give a stable single division of the worldwide sample. The original pathway categories and the broader display groups therefore remain the main guide.</p><p>The typical selected English sentence has about {result["readability_sensitivity"][0]["median_words_per_sentence"]:.0f} words. Sentence length describes the writing; actual compliance costs require separate evidence.</p>'))
 card.append(details)
 complexity.find('figcaption').string='Countries plotted close together use similar words in the selected English passages. Brown identifies the European shared-authorisation family. The chart describes language and institutions.'
 wording=sections['wording'];wording.h2.string='Read one country’s exact wording'
 p=wording.find('p');p.string='Choose a country below to see all its reviewed passages, with the original wording, a plain-language explanation and source links. The initial selection is the United Kingdom.'
 published=sections['published'];published.h2.string='How does this compare with published research?'
 backlog=sections['backlog'];backlog.h2.string='What the latest document review added'
 bd=ls.new_tag('details');bd['class']='context-details';bs=ls.new_tag('summary');bs.string='Review expansion, added countries and concrete examples';bd.append(bs)
 for child in list(backlog.contents):
  if child is not backlog.h2:bd.append(child.extract())
 backlog.append(bd)
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
 legal_js+="\nwindow.addEventListener('reliance-country',event=>{const iso=event.detail.iso3;if(countries.some(c=>c[0]===iso)){$('countrySelect').value=iso;$('quoteSearch').value='';renderClauses();}});"
 for script in ts.find_all('script'):script.extract()
 for script in ls.find_all('script'):script.extract()
 # Keep the source JSON payload untouched for data-integrity comparison.
 chart_json=BeautifulSoup(SOURCE.read_text('utf8'),'html.parser').find('script',id='chartData')
 main_timeline=''.join(str(x) for x in ts.body.contents)
 main_legal=''.join(str(x) for x in ls.body.contents)
 header=f'''<header class="combined-header"><div class="eyebrow">International pharmaceutical regulation</div><h1>How countries use foreign drug approvals—and what firms must still do</h1><p>The first chart shows the recorded spread of reliance rules. The second shows whose regulatory work can be used abroad. The third compares the conditions written into the rules and lets you read the underlying clauses.</p><div class="summary-strip"><span>250 countries and areas</span><span>Timeline: 2000–2025</span><span>{counts['national_authorisation_texts']} selected national approval pathways</span><span>{counts['jurisdictions_individually_reviewed']} jurisdiction text reviews</span></div><nav class="combined-nav"><a href="#timeline">1. Country timelines</a><a href="#authority-reach">2. Reference-authority reach</a><a href="#findings">3. Written conditions</a><a href="#wording">Country wording</a><a href="#methods">Completion and next steps</a></nav><p style="font-size:13px">The timeline uses dated historical records and the previously documented carry-forward and retrospective-list conventions. The wording review also includes later documents. Newly reviewed wording is assigned to historical years only when an operative date is established.</p></header>'''
 document='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>International pharmaceutical regulation — timelines, authority reach and legal wording</title><style>'+timeline_css+'\n'+legal_css+'\n'+TEMPLATE_CSS+'</style></head><body>'+header+'<main id="combinedMain"><div id="timelinePanels">'+main_timeline+'</div><div id="legalPanels">'+main_legal+'</div></main>'+str(chart_json)+'<script>(()=>{'+timeline_js+'})();</script><script>(()=>{'+legal_js+'})();</script></body></html>'
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(document,encoding='utf8')
 return dict(file=str(output),bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest())

outputs=[build(TIMELINE),build(O/'International_Pharmaceutical_Regulation.html')]
manifest=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),outputs=outputs,timeline_source=str(SOURCE),timeline_source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),wording_source=str(LEGAL),wording_source_sha256=hashlib.sha256(LEGAL.read_bytes()).hexdigest(),groups=HELP,data_policy='Display-only regrouping. No dates, categories, counts, links or legal coding changed.',panel_order=['Country-year heatmap','Reference-authority reach','Descending condition counts','Text comparison','Single-country exact wording','Published research','Review additions','Country audit','What is complete, and what resumes next?'])
(HERE/'combined_report_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(outputs,indent=2))
