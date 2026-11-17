"""Artifact agreement and offline browser interaction checks; no delivery data loaded."""
import json,re,argparse,csv,hashlib,os
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]

def check_static():
 r=json.loads((ROOT/'output/rankings.json').read_text());markup=(ROOT/'rr_auction_dashboard.html').read_text()
 data=json.loads(re.search(r'<script id="analysis-data" type="application/json">(.*?)</script>',markup,re.S)[1])
 assert data['rankings']==r
 evidence=json.loads((ROOT/'output/auction_brief_evidence.json').read_text())
 calls=json.loads((ROOT/'output/auction_calls.json').read_text())
 assert data['auctionBrief']['calls']==calls
 assert 'real_example' not in data['auctionBrief'],'Keep the optional dashboard aggregate-only'
 assert evidence['scoring_changed'] is False
 from refresh_player_status import action_for,validate_claim
 status_rows=list(csv.DictReader((ROOT/'data/reference/ipl_2027_player_status.csv').open(newline='')))
 status={str(x['player_id']):x for x in status_rows};review=data['statusReview']
 lock=json.loads((ROOT/'data/reference/official_rankings_lock.json').read_text())
 assert hashlib.sha256((ROOT/'output/rankings.json').read_bytes()).hexdigest()==lock['rankings_sha256']==review['rankings_sha256']
 assert len(status)==len(status_rows)==review['dataset_players']==1217
 assert data['eligibility']['excluded']==[]
 assert r['batters'][1]['player_id']==143
 assert any(x['player_id']==143 for x in data['players']['batters'])
 assert review['official_roster_unique_matched']==review['official_roster_records']==274 and not review['roster_unresolved']
 assert len([x for x in status_rows if x['priority_groups']!='remaining_pool'])==review['priority_unique_players']
 assert len([x for x in status_rows if x['auction_status']=='officially_listed'])==review['official_auction_entries']
 for pid,s in status.items():
  assert data['playerStatus'][pid]['auction_action']==s['auction_action']==action_for(s)[0]
  assert all(v!='' for k,v in s.items() if k!='field_source_ids'),(pid,'blank status field')
 for pid in ['1699','2756','3653']:assert status[pid]['auction_action']=='monitor for release'
 for pid in ['3644','4391']:assert status[pid]['ipl_2027_roster_status']=='traded_official' and status[pid]['auction_action']=='unavailable'
 for pid in ['4260','3125','781']:assert status[pid]['international_retirement_status']=='all_international_retired' and status[pid]['auction_action']!='unavailable'
 assert status['143']['ipl_retirement_status']=='retired' and status['143']['comeback_status']=='non_ipl_return_confirmed' and status['143']['auction_action']=='unavailable'
 # A future official commitment changes acquisition routing, not the frozen rank.
 target=dict(status['2756']);target.update(ipl_2027_roster_status='retained_official',ipl_2027_franchise='PBKS')
 assert action_for(target)[0]=='unavailable'
 target['ipl_2027_franchise']='RR';assert action_for(target)[0]=='already at RR'
 international=dict(status['2756']);international['international_retirement_status']='all_international_retired'
 assert action_for(international)[0]=='monitor for release'
 fake={'source_type':'credible_reporting','document_kind':'registration_report'}
 for field,value in [('auction_status','officially_listed'),('ipl_2027_roster_status','retained_official')]:
  try:validate_claim(field,value,fake,target)
  except ValueError:pass
  else:raise AssertionError('Reporting cannot certify an official listing/commitment')
 validate_claim('auction_status','officially_listed',{'source_type':'official','document_kind':'official_2027_auction_list'},target)
 for x in data['targetReviews']:
  assert x['auction_action']==status[str(x['player_id'])]['auction_action']
  fb=x['fallback'];assert fb['player_id']!=x['player_id'] and fb['evidence'] and fb['status_record']['sources']
  assert fb['auction_action']==status[str(fb['player_id'])]['auction_action']
 assert all(x['auction_action'] in ('monitor for release','pursue if listed') for x in data['shortlist'])
 excluded={x['player_id'] for x in data['eligibility']['excluded']}
 for cat in r:
  assert not excluded.intersection(x['player_id'] for x in data['players'][cat])
  for rows in data['scenarios'][cat].values():
   assert not excluded.intersection(x['player_id'] for x in rows)
 txt=(ROOT/'unstop_rankings.txt').read_text()
 pdf=PdfReader(ROOT/'output/pdf/rr_methodology_rankings.pdf')
 text='\n'.join(p.extract_text() for p in pdf.pages)
 first=pdf.pages[0].extract_text()
 for heading in ['Reliable Players Under Pressure','Top 10 batters','Top 10 bowlers',
                 'Define pressure before the ball','Measure quality and personal lift',
                 'Test reliability across matches','Build a consistent analysis sample',
                 'Limitations and reproducibility']:
  assert heading in text,heading
 for removed in ['snapshot','RR auction brief','RR auction call','monitor for release',
                 'Conditional target','Backup only','Before submission','Same-role fallback']:
  assert removed.lower() not in text.lower(),removed
 assert 'METHOD' in first and 'RANKINGS' in first
 example=evidence['real_example']
 worked_pages=[p.extract_text() for p in pdf.pages if 'From match state to pressure score' in p.extract_text()]
 assert len(worked_pages)==1
 worked=worked_pages[0]
 assert example['outcome_used_to_classify'] is False and example['pressure']>=example['threshold']
 assert abs(sum(example['pressure_components'].values())-example['pressure'])<1e-12
 for val in [str(example['match_id']),str(example['innings_ball_num']),example['display_delivery'],f"{example['score_before']}/{example['wickets_lost']}",f"{example['pressure']:.4f}"]:
  assert val in worked
 assert evidence['comparable_chase_death'][0]['pressure_deliveries']==44
 assert evidence['comparable_chase_death'][0]['without_example_match']['pressure_deliveries']==38
 for cat in r:
  rows=r[cat];assert len(rows)==10 and len({x['player_id'] for x in rows})==10
  assert [x['rank'] for x in rows]==list(range(1,11))
  expected=[x['name'] for x in rows]
  section=txt.split(cat.upper()+'\n')[1].split('\n\n')[0]
  assert [x.split(': ',1)[1] for x in section.splitlines()]==expected
  page=next(p.extract_text() for p in pdf.pages if 'Top 10 '+cat in p.extract_text())
  pos=[page.index(n) for n in expected];assert pos==sorted(pos)
  for x in rows:
   for field in ['pressure_score','absolute_pressure_index','own_ordinary_index']:
    assert f"{x[field]:.2f}" in page
   assert x['name'] in text
 assert data['audit']['joins']['delivery_count_before']==data['audit']['joins']['delivery_count_after']==200999
 assert sum(x['deliveries'] for x in data['audit']['exclusions_sequential'])+data['audit']['included']['deliveries']==200999
 assert 'including retired players' in ' '.join(text.split())
 assert 'The candidate screen excludes' not in text
 assert not re.search(r'<script[^>]+src=|<link[^>]+href=|fetch\(|XMLHttpRequest',markup)
 print('PASS: approved historical eligibility and ranking lock; JSON / HTML / PDF / dropdown names, order and scores; clean methodology report; one pre-ball worked example and aggregate evidence; status joins and authority gates; offline asset checks.')
 return r,len(pdf.pages)

def browser_checks(r):
 from playwright.sync_api import sync_playwright
 results={'errors':[],'requests':[]}
 dashboard_data=json.loads(re.search(r'<script id="analysis-data" type="application/json">(.*?)</script>',(ROOT/'rr_auction_dashboard.html').read_text(),re.S)[1])
 priority_count=dashboard_data['statusReview']['priority_unique_players']
 unavailable_priority=sum(x['priority_groups']!='remaining_pool' and x['auction_action']=='unavailable' for x in dashboard_data['playerStatus'].values())
 with sync_playwright() as p:
  b=p.chromium.launch(headless=True,executable_path=os.environ.get('RR_CHROMIUM_EXECUTABLE'))
  page=b.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1)
  page.on('pageerror',lambda err:results['errors'].append(str(err)))
  page.on('request',lambda req:results['requests'].append(req.url))
  page.goto((ROOT/'rr_auction_dashboard.html').as_uri())
  for cat in r:
   actual=page.locator(f'[data-category="{cat}"] .player-btn').all_text_contents()
   assert actual==[x['name'] for x in r[cat]]
  assert page.locator('#ranking-tables tbody tr').count()==20
  assert 'Primary submission' in page.locator('#submission-format').inner_text()
  assert page.locator('#submission-format a').first.get_attribute('href')=='output/pdf/rr_methodology_rankings.pdf'
  page.screenshot(path=str(ROOT/'tmp/dashboard-rankings.png'),full_page=True)
  page.locator('#rank-query').fill('Suryakumar');assert page.locator('#ranking-tables .player-btn').count()==1
  assert 'EXPLORATORY FILTERED VIEW' in page.locator('#ranking-status').inner_text()
  page.locator('#reset').click();assert page.locator('#ranking-tables .player-btn').count()==20
  for scenario in ['Broader pressure','Stricter pressure','IPL only','Scoring-heavy weights','Wicket-heavy weights']:
   page.locator('#scenario').select_option(label=scenario)
   assert 'EXPLORATORY ALTERNATIVE RANKING' in page.locator('#ranking-status').inner_text()
   assert page.locator('#ranking-tables tbody tr').count()==20
  page.locator('#category').select_option('bowlers');assert page.locator('#ranking-tables .tablebox').count()==1
  page.locator('#reset').click()
  page.get_by_role('button',name='Suryakumar Yadav',exact=True).click()
  assert page.locator('#compare').is_visible()
  assert page.locator('#comparison .player-name').all_text_contents()[0]=='Suryakumar Yadav'
  page.locator('#player-b').select_option(str(next(x['player_id'] for x in r['batters'] if x['name']=='Shashank Singh')))
  assert page.locator('#comparison .player-name').all_text_contents()[1]=='Shashank Singh'
  page.screenshot(path=str(ROOT/'tmp/dashboard-comparison.png'),full_page=True)
  page.locator('#compare-category').select_option('bowlers')
  assert page.locator('#comparison .player-name').all_text_contents()==[x['name'] for x in r['bowlers'][:2]]
  page.locator('#player-a').select_option(str(r['bowlers'][2]['player_id']))
  assert page.locator('#comparison .player-name').first.inner_text()=='Lockie Ferguson'
  page.locator('nav button[data-view="shortlist"]').click();assert page.locator('#shortlist .target').count()==6
  assert page.locator('#auction-call th').all_text_contents()==['Player','Proposed role','Strongest evidence','What would change the recommendation']
  assert 'Conditional target' in page.locator('[data-call-id="2756"]').inner_text()
  assert 'Backup only' in page.locator('[data-call-id="3653"]').inner_text()
  assert 'Backup only' in page.locator('[data-target-id="3653"]').inner_text()
  page.locator('#auction-call').screenshot(path=str(ROOT/'tmp/dashboard-auction-call.png'))
  assert page.locator('#action-summary tbody tr').count()==6
  assert str(priority_count)+' matching records' in page.locator('#status-count').inner_text()
  page.locator('#status-query').fill('Shashank')
  assert page.locator('#status-results details').count()==1
  page.locator('#status-results summary').click()
  assert 'PBKS 2026' in page.locator('#status-results').inner_text()
  assert page.locator('#status-results a[href="https://www.punjabkingsipl.in/players"]').count()==1
  page.locator('#status-query').fill('');page.locator('#status-action').select_option('unavailable')
  assert page.locator('#status-results details').count()==unavailable_priority
  assert 'Kuldeep Yadav' in page.locator('#status-results').inner_text() and 'Liam Livingstone' in page.locator('#status-results').inner_text()
  page.locator('#status-cohort').select_option('all');page.locator('#status-query').fill('Dinesh Karthik')
  assert page.locator('[data-status-id="143"]').count()==1
  page.locator('#status-results summary').click()
  assert 'SA20' in page.locator('#status-results').inner_text() and 'IPL playing retirement' in page.locator('#status-results').inner_text()
  page.locator('#status-action').select_option('all');page.locator('#status-query').fill('Klaasen')
  page.locator('#status-results summary').click()
  assert 'monitor for release' in page.locator('#status-results').inner_text()
  page.locator('#status-query').fill('Tilak');assert page.locator('[data-status-id="7897"]').count()==1
  page.locator('#status-query').fill('');assert '1217 matching records' in page.locator('#status-count').inner_text()
  assert page.locator('#status-results details').count()==60
  page.locator('#status-cohort').select_option('priority')
  page.screenshot(path=str(ROOT/'tmp/dashboard-shortlist.png'),full_page=True)
  page.locator('nav button[data-view="method"]').click()
  assert page.locator('#sensitivity tbody tr').count()==22
  assert page.locator('#role-evidence tbody tr').count()==8
  assert page.locator('#comparable-evidence tbody tr').count()==3
  assert '44 / 9' in page.locator('#comparable-evidence').inner_text()
  page.locator('#role-evidence').screenshot(path=str(ROOT/'tmp/dashboard-role-evidence.png'))
  page.screenshot(path=str(ROOT/'tmp/dashboard-method.png'),full_page=True)
  page.set_viewport_size({'width':390,'height':844})
  page.locator('nav button[data-view="rankings"]').click()
  assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
  page.screenshot(path=str(ROOT/'tmp/dashboard-mobile.png'),full_page=True)
  assert not results['errors'],results['errors']
  assert all(x.startswith('file:') for x in results['requests']),results['requests']
  b.close()
 print('PASS: ranking filters/alternatives/comparison; target actions and fallbacks; status search/cohort/action filters, aliases, retired comeback and international-only cases; mobile overflow; no JavaScript errors or network requests.')
 return results

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--browser',action='store_true');args=a.parse_args()
 r,npages=check_static();result={'static':'passed','pdf_pages':npages}
 if args.browser:result['browser']=browser_checks(r)
 (ROOT/'output/verification.json').write_text(json.dumps(result,indent=2))
