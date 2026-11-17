"""Build all review artifacts from the analysis JSON; no raw data is loaded."""
from pathlib import Path
import json,hashlib
from content import SOURCES,SQUAD,RULES,SHORTLIST,LIMITATIONS
from status_layer import get_status,enrich_shortlist,performance_evidence
from auction_brief import calls,phase
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output'
def load(x):return json.loads((OUT/x).read_text())
r=load('rankings.json');players=load('players.json');rob=load('robustness.json');scenarios=load('scenarios.json');audit=load('audit.json');diag=load('pressure_diagnostics.json');eligibility=load('eligibility.json')
status,status_sources=get_status();review=load('status_review_summary.json');snapshot=review['snapshot_date']
evidence=load('auction_brief_evidence.json');auction_calls=calls(evidence,status)
assert review['rankings_sha256']==hashlib.sha256((OUT/'rankings.json').read_bytes()).hexdigest(),'Refresh the status audit against the current frozen rankings'
assert evidence['rankings_sha256']==review['rankings_sha256']
short=[]
for s in SHORTLIST:
 z=dict(s);p=next(p for p in players[s['category']] if p['name']==s['name']);z['player_id']=p['player_id'];z['evidence']=f"Pooled rank {p['rank']}; score {p['pressure_score']:.2f}; adjusted lift {p['change']:+.2f}; {p['pressure_deliveries']} pressure attempts across {p['pressure_matches']} matches."
 z['evidence']+=f" IPL-only rank {rob[s['category']]['IPL only']['official_ranks'].get(str(p['player_id'])) or next((x['rank'] for x in scenarios[s['category']]['IPL only'] if x['player_id']==p['player_id']),'below exposure rule')}."
 if s['name']=='Shashank Singh':
  q=phase(evidence,'batters',2756,'Death');z['evidence']+=f" IPL death-phase index {q['pressure_index']:.2f} vs own {q['own_ordinary_index']:.2f}; lift {q['change']:+.2f} ({q['pressure_deliveries']} attempts / {q['pressure_matches']} matches)."
 if s['name']=='Avesh Khan':
  q=evidence['players']['3653']['ipl_only'];z['evidence']+=f" IPL-only score {q['pressure_score']:.2f}, lift {q['change']:+.2f}, {q['pressure_deliveries']} attempts / {q['pressure_matches']} matches. Bhuvneshwar's IPL-only score is {evidence['players']['360']['ipl_only']['pressure_score']:.2f}; the intervals overlap."
 short.append(z)
target_reviews=enrich_shortlist(short,players,status)
short=[x for x in target_reviews if x['auction_action'] in ('monitor for release','pursue if listed')]
data={'rankings':r,'players':players,'robustness':rob,'scenarios':scenarios,'audit':audit,'diagnostics':diag,'shortlist':short,'targetReviews':target_reviews,'sources':SOURCES,'squad':SQUAD,'rules':RULES,'limitations':LIMITATIONS,'eligibility':eligibility,'playerStatus':status,'statusSources':status_sources,'statusReview':review}
data['auctionBrief']={'calls':auction_calls,'phaseSplits':evidence['phase_splits'],'comparable':evidence['comparable_chase_death'],'subsetMethod':evidence['subset_method'],'cohortRule':evidence['cohort_rule'],'primary_submission':'output/pdf/rr_methodology_rankings.pdf','dashboard_format':'optional aggregate-only companion'}
(OUT/'auction_calls.json').write_text(json.dumps(auction_calls,indent=2))
(OUT/'refinement_summary.json').write_text(json.dumps({'snapshot_date':snapshot,'primary_submission':'output/pdf/rr_methodology_rankings.pdf','optional_format':'rr_auction_dashboard.html','dropdown_entry_file':'unstop_rankings.txt',
 'rankings_changed':True,'ranking_change_reason':'Retirement-only exclusions removed following organiser clarification and user-confirmed dropdown eligibility.','scoring_changed':False,'reproducible_scoring_error_found':False,'verified_dropdown_exclusion_found':False,'dropdown_access':'User confirmed retired players are included in the listing; the complete option list was not independently inspected.','rankings_sha256':evidence['rankings_sha256'],
 'reproducibility_checks':['Original input file hashes unchanged','Supplementary pooled A/O match existing selected-player outputs','Rebuilt IPL raw scores match existing IPL scenario outputs','One worked pressure state recomputed from earlier deliveries','Official ranking SHA-256 unchanged'],
 'recommendation_changes':{'Shashank Singh':'Conditional No. 6 depth target; phase checks narrow the pure-death claim; Jurel No. 3 refines RR fit.','Avesh Khan':'Backup only for provisional overs 17 and 19; attacking middle-over upgrade withdrawn. Compare Bhuvneshwar rather than infer superiority from IPL-only rank 3.'},
 'review_judgments':['Whether RR needs Indian No. 6 flexibility after retention','Whether Avesh or Bhuvneshwar fits reserve late-over needs better','Whether the pressure definition and historical mixed-league evidence justify the decision, with dropdown eligibility still to check']},indent=2))
(OUT/'auction_target_reviews.json').write_text(json.dumps(target_reviews,indent=2))
(OUT/'rankings_with_status.json').write_text(json.dumps({cat:[{**x,'status':status[str(x['player_id'])]} for x in rows] for cat,rows in r.items()},indent=2))
(OUT/'recommendation_changes.json').write_text(json.dumps({'snapshot_date':snapshot,'rankings_changed':False,'changes':[
 {'player_id':2756,'name':'Shashank Singh','before':'Conditional finishing priority','after':status['2756']['short_note'],'impact':'Narrowed to Indian No. 6 depth, entering around overs 11-15; negative IPL death lift limits the death-specialist claim. Tewatia remains a conditional comparison/fallback.'},
 {'player_id':3653,'name':'Avesh Khan','before':'Role-led middle/death priority','after':status['3653']['short_note'],'impact':'Downgraded to backup for provisional overs 17 and 19. Remove middle-over upgrade claim; IPL phase evidence and Bhuvneshwar comparison do not establish a superior first-choice buy.'},
 {'player_id':4246,'name':'Nitish Rana','before':'Availability unconfirmed','after':status['4246']['short_note'],'impact':'Monitor DC release; Tilak is a conditional MI fallback.'},
 {'player_id':4692,'name':'Lockie Ferguson','before':'Availability unconfirmed','after':status['4692']['short_note'],'impact':'Monitor PBKS release; Hazlewood is the conditional pace fallback.'},
 {'player_id':4373,'name':'Mustafizur Rahman','before':'Reported registration, clearance unconfirmed','after':status['4373']['short_note'],'impact':'Remain clearance-first, pursue only if officially listed; Boult is a conditional left-arm alternative.'},
 {'player_id':3374,'name':'Mark Chapman','before':'Eligibility and registration unconfirmed','after':status['3374']['short_note'],'impact':'Scouting only, pursue if listed; Miller offers IPL experience but weaker pressure lift.'},
 {'player_id':3644,'name':'Kuldeep Yadav','before':'No explicit franchise commitment note','after':status['3644']['short_note'],'impact':'Keep bowling rank 10; unavailable for auction acquisition following official LSG trade.'},
 {'player_id':4391,'name':'Liam Livingstone','before':'No explicit franchise commitment note','after':status['4391']['short_note'],'impact':'Not an auction fallback after official CSK trade.'}],
 'no_priority_removed':'None of the original six target cards has a verified 2027 commitment or IPL retirement. Their acquisition gates are now explicit. No target is verified officially listed.'},indent=2))
(OUT/'auction_shortlist.json').write_text(json.dumps(short,indent=2));(OUT/'sources.json').write_text(json.dumps(SOURCES,indent=2))
# HTML is one file: embedded aggregates, CSS and JavaScript. No network requests.
from dashboard_ui import render_dashboard
render_dashboard(ROOT,data)

from methodology_report import build_report
path=build_report(ROOT,r,rob,audit,evidence,{cat:len(rows) for cat,rows in players.items()})

# Exact final lists for dropdown entry; no auction-status commentary.
text='SupeRR Selector Season 2 - Round 1\nFinal player rankings\n\n'
for cat,rows in r.items():
 text+=cat.upper()+'\n'+'\n'.join(f'Rank {x["rank"]}: {x["name"]}' for x in rows)+'\n\n'
text+='Enter each list in rank order, using the matching names in the Unstop dropdowns.\n'
text+='Methodology report: output/pdf/rr_methodology_rankings.pdf\n'
(ROOT/'unstop_rankings.txt').write_text(text)
print('Built dashboard and',path)
