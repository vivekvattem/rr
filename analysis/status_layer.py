"""Shared presentation layer for the dashboard, PDF and auction JSON.

All current status comes from the refreshable reference CSV. Performance remains
the frozen model output; no availability-based re-scoring happens here.
"""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FALLBACKS={
 2756:(3926,'Rahul Tewatia','Indian finisher, No. 6-7','Same Indian finishing slot; markedly weaker pressure evidence. A role backup, not a statistical substitute.'),
 3653:(360,'Bhuvneshwar Kumar','Indian pace, new-ball and death cover','Slightly better IPL death-phase point estimates; intervals overlap. Prefer if new-ball cover also matters. RCB release and official listing remain unconfirmed.'),
 4246:(7897,'Tilak Varma','Indian left-hand middle-order batter, No. 3-5','Same handedness and middle-order role; acquiring him also depends on MI releasing him.'),
 4692:(830,'Josh Hazlewood','Overseas pace, powerplay/middle overs','Same overseas pace slot; control-led rather than Ferguson pace. IPL pressure exposure remains below the sample rule.'),
 4373:(2320,'Trent Boult','Overseas left-arm pace','Same left-arm pace slot; strongest deployment is new ball rather than a like-for-like two-over death role.'),
 3374:(1077,'David Miller','Overseas left-hand middle-order/finishing batter','Same left-hand overseas batting slot; more finishing and less No. 3-4 rebuilding. Pressure lift is negative.'),
 1699:(7897,'Tilak Varma','Indian middle-order accelerator','MI teammate in a comparable middle-order slot. Both depend on release; neither is a confirmed auction opportunity.')}

def get_status():
 with (ROOT/'data/reference/ipl_2027_player_status.csv').open(newline='') as f:rows=list(csv.DictReader(f))
 assert len({int(x['player_id']) for x in rows})==len(rows),'Status join must be one-to-one'
 sources=list(csv.DictReader((ROOT/'data/reference/status_sources.csv').open(newline='')))
 smap={s['source_id']:s for s in sources}
 for x in rows:
  x['player_id']=int(x['player_id']);x['sources']=[smap[s] for s in x['source_ids'].split(' | ') if s in smap]
  x['short_note']=status_note(x)
 return {str(x['player_id']):x for x in rows},sources

def status_note(s):
 team=s['latest_verified_ipl_franchise'];season=s['latest_verified_ipl_season']
 if s['ipl_2027_roster_status'] in ('traded_official','retained_official'):
  return f"{s['ipl_2027_franchise']} 2027 committed; {s['auction_action']}"
 if s['auction_action']=='unavailable':return 'Unavailable: '+s['ipl_retirement_scope']
 if s['auction_action']=='already at RR':return 'RR 2026 roster option; 2027 status pending'
 if s['auction_action']=='monitor for release':return f'{team} {season}; target only if released'
 if s['player_id']==4373:return 'KKR 2026 release; 2027 listing/clearance unconfirmed'
 return f"{team+' '+season if team!='unknown' else 'IPL franchise unverified'}; pursue only if listed"

def performance_evidence(p):
 return f"Pooled rank {p['rank']}; score {p['pressure_score']:.2f}; lift {p['change']:+.2f}; {p['pressure_deliveries']} pressure attempts / {p['pressure_matches']} matches; {p['ipl_pressure_deliveries']} IPL pressure attempts."

def enrich_shortlist(short,players,status):
 result=[]
 for old in short:
  x=dict(old);s=status[str(x['player_id'])];x.update(auction_action=s['auction_action'],status_record=s,
   status=s['short_note']+'. '+('Official 2027 auction entry verified; price unconfirmed.' if s['auction_status']=='officially_listed' else 'Official 2027 auction entry and price unconfirmed.'))
  if s['other_franchise_commitments']!='unknown':x['status']+=' Other-league commitment: '+s['other_franchise_commitments']+'.'
  if x['player_id']==4373:x['status']+=' Registration process is reported by India Today (11 Nov 2026); not official auction entry. Require explicit regulatory clearance.'
  fid,name,role,tradeoff=FALLBACKS[x['player_id']];fs=status[str(fid)]
  fp=next(p for p in players[x['category']] if p['player_id']==fid)
  x['fallback']={'player_id':fid,'name':name,'role':role,'tradeoff':tradeoff,'evidence':performance_evidence(fp),
    'auction_action':fs['auction_action'],'status':fs['short_note'],'status_record':fs}
  result.append(x)
 return result
