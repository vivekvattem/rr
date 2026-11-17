"""Materialize a dated, ID-safe status register. Reads local files; never uses the network.

Public roster facts and curated source/claim CSVs are the inputs. Unknown is a real
state, not an assertion that a player is active, free, registered or eligible.
"""
import argparse,csv,json,re,unicodedata,hashlib
from collections import Counter,defaultdict
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];REF=ROOT/'data/reference';OUT=ROOT/'output'
def normalize(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower())
def read_csv(name):
 with (REF/name).open(newline='') as f:return list(csv.DictReader(f))
def save_csv(path,rows,fields=None):
 with path.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)

def action_for(row):
 """Acquisition policy, independent of pressure rank and international retirement."""
 if row['ipl_retirement_status']=='retired' or row['franchise_t20_retirement_status']=='all_professional_retired' or row['auction_status']=='withdrawn_confirmed':
  return 'unavailable','Confirmed retirement/withdrawal blocks an IPL playing acquisition; see scope/effective date.'
 if row['ipl_2027_roster_status'] in ('retained_official','traded_official'):
  if row['ipl_2027_franchise']=='RR':return 'already at RR','Official 2027 commitment to RR; existing squad option.'
  return 'unavailable','Official 2027 commitment to '+row['ipl_2027_franchise']+'; remove from auction acquisition list.'
 if row['ipl_2027_roster_status']=='released_official':
  return 'pursue if listed','Official 2027 release; conditional on official auction listing and any applicable clearance.'
 if row['latest_verified_ipl_franchise']=='RR' and row['latest_verified_ipl_season']=='2026':
  return 'already at RR','2026 RR roster-history option only; 2027 retention and replacement rights remain unknown.'
 if row['latest_verified_ipl_season']=='2026' and row['auction_status'] not in ('released_conditional','officially_listed','out_of_contract_conditional'):
  return 'monitor for release','Target only if released from '+row['latest_verified_ipl_franchise']+' and officially listed for the 2027 auction.'
 return 'pursue if listed','Conditional candidate only: official 2027 auction entry and any applicable clearance must be verified.'

def validate_claim(field,value,source,known_fields):
 if field in ('ipl_2027_roster_status','ipl_2027_franchise') and source['source_type']!='official':
  raise ValueError('2027 commitments require an official source')
 if field=='auction_status' and value=='officially_listed' and (source['source_type']!='official' or source.get('document_kind')!='official_2027_auction_list'):
  raise ValueError('Auction entry requires the official 2027 auction list')
 if field not in known_fields:raise ValueError('Unknown status field: '+field)

def main(data_dir,as_of):
 mapping=pd.read_csv(Path(data_dir)/'competition_team_player_mapping.csv')
 lock=json.loads((REF/'official_rankings_lock.json').read_text())
 assert hashlib.sha256((OUT/'rankings.json').read_bytes()).hexdigest()==lock['rankings_sha256'],'Official rankings changed: review verified dropdown evidence before updating the lock'
 names=mapping.groupby('player_id').player_name.agg(lambda x: sorted(set(x))).to_dict()
 names={int(k):v for k,v in names.items()};by_name=defaultdict(set)
 for pid,ns in names.items():
  for n in ns:by_name[normalize(n)].add(pid)
 sources={s['source_id']:s for s in read_csv('status_sources.csv')}
 aliases=read_csv('player_aliases.csv');alias_ids={normalize(x['public_alias']):int(x['player_id']) for x in aliases}
 assert all(x in names for x in alias_ids.values()),'Alias points outside supplied player pool'
 rosters=json.loads((REF/'public_rosters_2026.json').read_text())
 membership=mapping[mapping.comp_name=='IPL 2026'].groupby('team_name').player_id.agg(set).to_dict()
 roster_by_id={};join_review=[];official_rows=[]
 for code,team in rosters.items():
  assert team['season']==2026,'Review the fetched season before materializing'
  if team['verification_date']>as_of:raise ValueError('Public roster snapshot is later than requested cutoff')
  for public in team['players']:
   n=public['name'];candidates=sorted(by_name.get(normalize(n),set()));pid=None;method='exact_normalized'
   if normalize(n) in alias_ids:
    pid=alias_ids[normalize(n)];method='curated_alias'
    assert pid in membership.get(team['team'],set()),'Re-review curated alias: '+n
   elif len(candidates)==1:pid=candidates[0]
   elif len(candidates)>1:
    scoped=[x for x in candidates if x in membership.get(team['team'],set())]
    if len(scoped)==1:pid=scoped[0];method='homonym_resolved_by_2026_team_membership'
   review={'public_name':n,'public_franchise':code,'candidate_player_ids':'|'.join(map(str,candidates)),
           'matched_player_id':pid if pid is not None else 'unknown','match_method':method if pid else 'unresolved',
           'review_required':'no' if pid else 'yes','source_url':team['page_url']}
   if method!='exact_normalized' or pid is None:join_review.append(review)
   official_rows.append(review)
   if pid is None:continue
   assert pid not in roster_by_id,'Public roster duplicate player identity across teams'
   roster_by_id[pid]={'code':code,'team':team,'name':n,'method':method}
 assert len(official_rows)==sum(len(x['players']) for x in rosters.values())
 priority={};rankings=json.loads((OUT/'rankings.json').read_text())
 for cat in ('batters','bowlers'):
  for x in pd.read_csv(OUT/(cat+'_all.csv')).head(25).to_dict('records'):
   priority.setdefault(int(x['player_id']),[]).append(cat+('_top10' if x['rank']<=10 else '_next15'))
 target_ids={2756,3653,4246,4692,4373,3374,1699};fallback_ids={3926,360,7897,830,2320,1077}
 for pid in target_ids:priority.setdefault(pid,[]).append('RR_target_or_benchmark')
 for pid in fallback_ids:priority.setdefault(pid,[]).append('RR_same_role_fallback')
 events=read_csv('status_events.csv');events_by_id=defaultdict(list)
 for e in events:
  pid=int(e['player_id']);assert pid in names
  assert e['source_id'] in sources
  if e['verification_date']<=as_of and (e['announcement_date']=='unknown' or e['announcement_date']<=as_of):events_by_id[pid].append(e)
 result=[];evidence=[]
 for pid in sorted(names):
  row={'player_id':pid,'dataset_name':names[pid][0],'canonical_name':names[pid][0],
       'aliases':' | '.join(sorted(set(names[pid]+[x['public_alias'] for x in aliases if int(x['player_id'])==pid]))),
       'latest_verified_ipl_franchise':'unknown','latest_verified_ipl_season':'unknown','roster_2026_franchise':'unknown',
       'ipl_retirement_status':'unknown','ipl_retirement_scope':'unknown','ipl_retirement_effective_date':'unknown',
       'franchise_t20_retirement_status':'unknown','franchise_t20_retirement_scope':'unknown',
       'international_retirement_status':'unknown','international_retirement_scope':'unknown','international_retirement_effective_date':'unknown',
       'comeback_status':'unknown','comeback_scope':'unknown','comeback_date':'unknown',
       'ipl_2027_roster_status':'unknown','ipl_2027_franchise':'unknown','auction_status':'unknown',
       'reported_auction_status':'unknown','reported_roster_status':'unknown','conflict_notes':'unknown','other_retirement_scope':'unknown',
       'regulatory_clearance_status':'unknown','other_franchise_commitments':'unknown',
       'identity_match_status':'dataset_id','priority_groups':' | '.join(priority.get(pid,[])) or 'remaining_pool',
       'dropdown_eligibility':'unknown','snapshot_date':as_of}
  refs=set();ann=[];effective=[];verified=[];field_sources={}
  if pid in roster_by_id:
   rr=roster_by_id[pid];team=rr['team'];sid='ROSTER_'+rr['code'];refs.add(sid)
   row.update(roster_2026_franchise=rr['code'],latest_verified_ipl_franchise=rr['code'],latest_verified_ipl_season='2026',
              ipl_2027_roster_status='pending_2026_roster',identity_match_status=rr['method'])
   if normalize(rr['name'])==normalize(names[pid][0]):row['canonical_name']=rr['name']
   verified.append(team['verification_date']);field_sources['latest_verified_ipl_franchise']=sid
  for e in sorted(events_by_id[pid],key=lambda z:(z['announcement_date'] if z['announcement_date']!='unknown' else '0000',z['event_id'])):
   source=sources[e['source_id']];field=e['field'];value=e['value']
   # Reports may describe a process, never certify a commitment or auction listing.
   validate_claim(field,value,source,row)
   row[field]=value;field_sources[field]=e['source_id'];refs.add(e['source_id'])
   if e['announcement_date']!='unknown':ann.append(e['announcement_date'])
   if e['effective_date']!='unknown':effective.append(e['effective_date'])
   verified.append(e['verification_date'])
   evidence.append({**e,'canonical_name':row['canonical_name'],'source_url':source['url'],'source_type':source['source_type'],'source_title':source['title'],'source_publication_date':source['publication_date']})
  row['auction_action'],row['auction_action_reason']=action_for(row)
  row['review_depth']=('priority_source_review' if pid in priority else 'official_roster_review' if pid in roster_by_id else 'documented_event_review' if events_by_id[pid] else 'retirement_register_screen_only')
  row['retirement_screen_result']='documented_event' if any((x['field'] in ('ipl_retirement_status','international_retirement_status') and x['value'] not in ('unknown','active')) or x['field']=='other_retirement_scope' or (x['field']=='franchise_t20_retirement_status' and x['value'] in ('all_professional_retired','indian_cricket_retired_other_leagues_permitted','resumed_non_ipl_franchise')) for x in events_by_id[pid]) else 'no_match_in_reviewed_registers_status_unknown'
  row['source_ids']=' | '.join(sorted(refs)) or 'unknown'
  row['source_url']=' | '.join(sorted({sources[s]['url'] for s in refs})) or 'unknown'
  row['official_source_urls']=' | '.join(sorted({sources[s]['url'] for s in refs if sources[s]['source_type']=='official'})) or 'unknown'
  row['reporting_source_urls']=' | '.join(sorted({sources[s]['url'] for s in refs if sources[s]['source_type']!='official'})) or 'unknown'
  row['field_source_ids']=json.dumps(field_sources,sort_keys=True,separators=(',',':'))
  row['announcement_date']=max(ann) if ann else 'unknown';row['effective_date']=max(effective) if effective else 'unknown'
  row['verification_date']=max(verified) if verified else 'unknown'
  row['screen_verification_date']=as_of
  result.append(row)
 save_csv(REF/'ipl_2027_player_status.csv',result)
 save_csv(REF/'player_status_evidence.csv',evidence)
 save_csv(REF/'alias_join_review.csv',join_review)
 save_csv(REF/'official_roster_identity_join.csv',official_rows)
 # Compare supplied 2026 membership to externally published roster history, without
 # inventing an official franchise for a dataset-only player.
 dataset_2026=set(mapping.loc[mapping.comp_name=='IPL 2026','player_id']);public_ids=set(roster_by_id)
 data_only=sorted(dataset_2026-public_ids)
 summary={'snapshot_date':as_of,'dataset_players':len(result),'retirement_register_screened':len(result),
  'official_roster_records':len(official_rows),'official_roster_unique_matched':len(public_ids),
  'roster_by_team':{c:len(v['players']) for c,v in rosters.items()},'roster_unresolved':[x for x in official_rows if x['review_required']=='yes'],
  'alias_or_homonym_reviews':len(join_review),'curated_aliases':len(aliases),'roster_aliases_resolved':sum(x['match_method']=='curated_alias' for x in join_review),'homonyms_resolved':sum('homonym' in x['match_method'] for x in join_review),
  'priority_unique_players':len(priority),'review_depth_counts':dict(Counter(x['review_depth'] for x in result)),
  'dataset_2026_players':len(dataset_2026),'dataset_only_2026_players':[{'player_id':p,'name':names[p][0]} for p in data_only],
  'documented_retirement_players':sum(x['retirement_screen_result']=='documented_event' for x in result),
  'ipl_retirement_confirmed':sum(x['ipl_retirement_status']=='retired' for x in result),
  'official_2027_committed':sum(x['ipl_2027_roster_status'] in ('traded_official','retained_official') for x in result),
  'official_auction_entries':sum(x['auction_status']=='officially_listed' for x in result),
  'unknown_auction_status':sum(x['auction_status']=='unknown' for x in result),
  'unknown_ipl_retirement_status':sum(x['ipl_retirement_status']=='unknown' for x in result),
  'unknown_international_retirement_status':sum(x['international_retirement_status']=='unknown' for x in result),
  'screen_sources':['RETIREMENTS_ICC_2023_24','RETIREMENTS_ICC_2024_25','RETIREMENTS_2026_DISCOVERY'],
  'scope_note':'Every supplied ID was matched against reviewed retirement registers. This is not an individual exhaustive news search for all 1,217 people. Unknown cases are unresolved, not certified active or auction eligible. Official 2026 roster histories include replacements and superseded signings; 2027 commitments require separate announcements.',
  'auction_list_search':('Official IPL 2027 auction list entries verified for '+str(sum(x['auction_status']=='officially_listed' for x in result))+' reviewed IDs; other cases remain unresolved.' if any(x['auction_status']=='officially_listed' for x in result) else 'No official IPL 2027 auction list located in official IPL searches as of this snapshot; a reported registration is not entry.'),
  'rankings_sha256':hashlib.sha256((OUT/'rankings.json').read_bytes()).hexdigest(),
  'rankings_policy':'Historical rankings include retired players who meet the sample rules. User confirmed retired players appear in the dropdown listing. Availability applies only to the separate acquisition research; exact dropdown aliases remain to be checked.'}
 (OUT/'status_review_summary.json').write_text(json.dumps(summary,indent=2))
 print(json.dumps(summary,indent=2))

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--data-dir',required=True);a.add_argument('--as-of',default='2026-11-13');args=a.parse_args();main(args.data_dir,args.as_of)
