"""Local supplementary evidence for the auction brief; never changes rankings.

Reuses the frozen pressure/peer formulas. Exports aggregate role/context summaries
and exactly one explicitly requested, traceable delivery example. No other
delivery-level records are written or transmitted.
"""
import argparse,hashlib,json
from pathlib import Path
import pandas as pd
import analyze as model

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output'
def subset_summary(d,pid,mask):
 q=d[d.pid.eq(pid)];h=q.loc[mask.reindex(q.index,fill_value=False)&q.high]
 phases=set(h.phase);o=q[(~q.high)&q.phase.isin(phases)]
 n=len(h);A=h.utility.sum()/(n+150);O=h['own'].mean()
 return {'player_id':pid,'name':q['name'].mode().iloc[0],'pressure_deliveries':n,'pressure_matches':int(h.match_id.nunique()),
  'ordinary_reference_deliveries':len(o),'pressure_legal_balls':int(h.legal.sum()),'runs':float(h.run.sum()),'wickets':int(h.wicket.sum()),
  'runs_per_100_attempts':float(100*h.run.mean()),'economy':float(6*h.run.sum()/max(h.legal.sum(),1)),
  'wicket_pct':float(100*h.wicket.mean()),'pressure_index':float(50+20*A),'own_ordinary_index':float(50+20*O),'change':float(20*(A-O)),
  'peer_economy':float(6*h.peer_run.sum()/max(h.legal.sum(),1)),
  'supported':bool(n>=30 and len(o)>=30 and h.match_id.nunique()>=4)}

def main(path):
 before=hashlib.sha256((OUT/'rankings.json').read_bytes()).hexdigest()
 b,audit=model.load_data(path);b=model.pressure(b)
 prior=json.loads((OUT/'audit.json').read_text());assert audit['included']==prior['included']
 assert all(v['sha256']==prior['files'][k]['sha256'] for k,v in audit['files'].items())
 saved=json.loads((OUT/'players.json').read_text());scenarios=json.loads((OUT/'scenarios.json').read_text())
 ids={'batters':[2756,3926,3297,7260],'bowlers':[3653,360]};evidence={'rankings_sha256':before,'scoring_changed':False,'snapshot_date':'2026-11-13','players':{},'phase_splits':{}}
 fitted={}
 for cat in ids:
  full=model.peer_residual(b,cat,b.pressure.ge(.62));_,full=model.fit(full,cat,False)
  ipl=b[b.league.eq('IPL')].copy();di=model.peer_residual(ipl,cat,ipl.pressure.ge(.62));ri,di=model.fit(di,cat,False);fitted[cat]=di
  evidence['phase_splits'][cat]=[]
  for pid in ids[cat]:
   p=next(x for x in saved[cat] if x['player_id']==pid);si=next(x for x in scenarios[cat]['IPL only'] if x['player_id']==pid)
   summary=subset_summary(full,pid,pd.Series(True,index=full.index))
   # Same A/O as the existing official outputs; no fresh scoring policy.
   assert abs(summary['pressure_index']-p['absolute_pressure_index'])<1e-10
   assert abs(summary['own_ordinary_index']-p['own_ordinary_index'])<1e-10
   recomputed=ri[ri.player_id.eq(pid)].iloc[0]
   assert abs(recomputed.raw_score-si['raw_score'])<1e-10
   evidence['players'][str(pid)]={'pooled':p,'ipl_only':si}
   for phase in ['Middle','Death']:
    z=subset_summary(di,pid,di.phase.eq(phase));z['phase']=phase;z['league']='IPL';z['context']='IPL-only peer model, both innings'
    evidence['phase_splits'][cat].append(z)
 # A worked illustration selected after the historical analysis, never used to
 # select players or fit their rankings. Cohort filters do not use ball outcomes.
 key={'match_id':30072,'innings':2,'innings_ball_num':117}
 z=b
 for k,v in key.items():z=z[z[k].eq(v)]
 assert len(z)==1
 x=z.iloc[0];assert x.striker_id==2756 and x.legal and x.pressure>=.62
 U=1-x.balls_left/120;D=min(x.lost/7,1);R=x.demand_ratio
 parts={'demand':.45*min(R/1.4,1),'urgency':.35*U,'wicket_depletion':.20*D}
 example={**key,'competition':x.comp_name,'match_number':str(x.match_number),'date':x.match_date,
  'home_team':x.home_team,'away_team':x.away_team,'striker_id':int(x.striker_id),'striker':x.striker_name,
  'bowler_id':int(x.bowler_id),'bowler':x.bowler_name,'overid':int(x.overid),'over_ball_num':float(x.over_ball_num),
  'legal_balls_used':int(x.balls_used),'display_delivery':f'{int(x.balls_used)//6}.{int(x.balls_used)%6+1}',
  'score_before':int(x.score_before),'wickets_lost':int(x.lost),'wickets_in_hand':int(x.wickets_left),
  'balls_remaining':int(x.balls_left),'target':int(x.target),'runs_required':int(x.runs_needed),
  'required_rate_per_over':float(6*x.runs_needed/x.balls_left),'base_rpb':float(x.base_rpb),'resource_rpb':float(x.resource_rate),
  'demand_ratio':float(R),'urgency':float(U),'depletion':float(D),'pressure_components':parts,'pressure':float(x.pressure),
  'threshold':.62,'ball_runs':int(x.runs),'outcome_used_to_classify':False,
  'public_match_source':'https://www.iplt20.com/news/article/tata-ipl-2024-match-17-gt-vs-pbks-match-report'}
 assert abs(sum(parts.values())-x.pressure)<1e-12 and int(x.balls_used)+int(x.balls_left)==120
 evidence['real_example']=example
 di=fitted['batters'];mask=di.innings.eq(2)&di.phase.eq('Death')
 comparable=[]
 for pid in [2756,3926,3297]:
  z=subset_summary(di,pid,mask);z['context']='IPL chases, overs 16-20, pre-ball P >= 0.62; live demand gate 0.65-1.80'
  # Keep the selected match out as an explicit check against one-game storytelling.
  without=subset_summary(di[di.match_id.ne(key['match_id'])],pid,mask)
  z['without_example_match']={k:without[k] for k in ['pressure_deliveries','pressure_matches','runs','wickets','runs_per_100_attempts']}
  comparable.append(z)
 evidence['comparable_chase_death']=comparable
 close=subset_summary(di,2756,mask&di.wickets_left.between(3,6))
 evidence['closer_resource_subset']={k:close[k] for k in ['pressure_deliveries','pressure_matches','runs','wickets','runs_per_100_attempts','supported']}
 evidence['closer_resource_subset']['context']='Same chase/death/P filters plus 3-6 wickets in hand, including the example. Below 30 pressure opportunities: descriptive only.'
 evidence['cohort_rule']='Declared by league, chase innings, death phase and existing P cutoff; no runs/outcome filter. These are comparable model contexts, not identical match difficulty or a causal role comparison.'
 evidence['subset_method']='Phase/chase summaries reuse the IPL-only ordinary peer model, 150-attempt pressure shrinkage and that player\'s 100-attempt-shrunk ordinary phase reference. Raw rates are descriptive. No new ranking or phase score is created; phase indices have their own shrinkage and are not additive.'
 evidence['interpretation']={'Shashank Singh':'Conditional No. 6 depth option, entering around overs 11-15 and carrying into the death. Overall lift and the Tewatia comparison support a watchlist place; negative adjusted death lift limits a pure death-specialist claim.',
  'Avesh Khan':'Backup for two late overs, provisionally 17 and 19, if RR needs Indian pace cover. IPL-only rank 3 is credible but only marginally ahead of Bhuvneshwar (rank 4); death-phase point estimates favour Bhuvneshwar. Do not recommend a middle-over upgrade from the IPL split.'}
 assert hashlib.sha256((OUT/'rankings.json').read_bytes()).hexdigest()==before
 (OUT/'auction_brief_evidence.json').write_text(json.dumps(model.clean(evidence),indent=2,allow_nan=False))
 print('Saved supplementary aggregates and one delivery example; official rankings unchanged.')
 print(json.dumps({'example':example,'comparable':comparable,'closer':evidence['closer_resource_subset']},indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data-dir',type=Path,required=True);args=p.parse_args();main(args.data_dir)
