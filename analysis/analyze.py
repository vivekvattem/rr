"""Local, deterministic pressure analysis. No raw deliveries are exported."""
from pathlib import Path
import argparse, json, hashlib, re
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

SEED=202711; AS_OF='2026-11-13'; BOOT=400
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'output'
# Round 1 ranks historical performance. Retirement and acquisition availability
# do not determine eligibility; the user confirmed retired players are listed.
# See data/reference/historical_eligibility_policy.json for the policy evidence.
EXCLUSIONS={}

def clean(x):
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [clean(v) for v in x]
    if isinstance(x,np.generic): return clean(x.item())
    if isinstance(x,float) and not np.isfinite(x): return None
    return x

def dump(name,x):
    (OUT/name).write_text(json.dumps(clean(x),indent=2,allow_nan=False))

def load_data(path):
    fs={p.stem:pd.read_csv(p,low_memory=False) for p in path.glob('*.csv')}
    b=fs['ball_by_ball']; m=fs['matches']; c=fs['competitions']; xi=fs['playing_eleven']; mp=fs['competition_team_player_mapping']; t=fs['teams']
    audit={'as_of':AS_OF,'files':{},'joins':{}}
    for k,d in fs.items():
        audit['files'][k]={'rows':len(d),'columns':list(d),'nulls':d.isna().sum().to_dict(),'sha256':hashlib.sha256((path/(k+'.csv')).read_bytes()).hexdigest()}
    for name,d,key in [('matches',m,['match_id']),('competitions',c,['comp_id']),('teams',t,['comp_id','team_id']),('mapping',mp,['comp_id','team_id','player_id']),('xi',xi,['match_id','team_id','player_id'])]:
        audit['joins'][name+'_duplicate_keys']=int(d.duplicated(key).sum())
    b=b.merge(m,on='match_id',how='left',validate='many_to_one',indicator=True)
    audit['joins']['unmatched_match_deliveries']=int(b._merge.ne('both').sum()); b=b.drop(columns='_merge')
    b=b.merge(c,on='comp_id',how='left',validate='many_to_one',indicator=True)
    audit['joins']['unmatched_competition_deliveries']=int(b._merge.ne('both').sum());b=b.drop(columns='_merge')
    for role,team,player in [('striker','batting_team_id','striker_id'),('non_striker','batting_team_id','non_striker_id'),('bowler','bowling_team_id','bowler_id')]:
        for label,d,keys in [('mapping',mp,['comp_id','team_id','player_id']),('xi',xi,['match_id','team_id','player_id'])]:
            dd=d.drop_duplicates(keys)[keys].rename(columns={'team_id':team,'player_id':player})
            j=b.merge(dd,on=[keys[0],team,player],how='left',validate='many_to_one',indicator=True)
            assert len(j)==len(b)
            audit['joins'][role+'_'+label+'_unmatched_deliveries']=int(j._merge.ne('both').sum())
    for team in ['batting_team_id','bowling_team_id']:
        j=b.merge(t.rename(columns={'team_id':team}),on=['comp_id',team],how='left',validate='many_to_one',indicator=True)
        assert len(j)==len(b);audit['joins'][team+'_unmatched_deliveries']=int(j._merge.ne('both').sum())
    audit['joins']['delivery_count_before']=len(fs['ball_by_ball']);audit['joins']['delivery_count_after']=len(b)
    assert len(b)==len(fs['ball_by_ball'])
    audit['metadata_matches_without_deliveries']=sorted(set(m.match_id)-set(b.match_id))
    audit['metadata_competitions_without_matches']=c[~c.comp_id.isin(m.comp_id)].to_dict('records')
    audit['coverage']=b.groupby(['comp_name','match_format','season']).agg(deliveries=('match_id','size'),matches=('match_id','nunique'),start=('match_date','min'),end=('match_date','max')).reset_index().to_dict('records')
    audit['extras']=b.groupby('extras_type',dropna=False).agg(deliveries=('runs','size'),bat_runs=('runs','sum'),extras1=('extras1_runs','sum'),extras2=('extras_2_runs','sum')).reset_index().fillna('none').to_dict('records')
    audit['dismissals']=b.groupby('dismissal_type',dropna=False).size().rename('n').reset_index().fillna('none').to_dict('records')
    audit['duplicate_delivery_keys']=int(b.duplicated(['match_id','innings','innings_ball_num']).sum())
    b=b.sort_values(['match_id','innings','innings_ball_num']).reset_index(drop=True)
    b['league']=np.where(b.comp_name.str.match(r'^IPL \d{4}$'),'IPL',np.where(b.match_format.eq('T20I'),'T20I','Other T20'))
    b['year']=b.match_date.str[:4].astype(int)
    b['legal']=~b.extras_type.isin(['wide','Overstep','other'])
    b['team_runs']=b.runs+b.extras1_runs+b.extras_2_runs
    b['charged']=b.runs+np.where(b.extras_type.isin(['wide','Overstep','other']),b.extras1_runs,0)
    # Secondary no-ball extras are byes/legbyes: not charged to bowler.
    b['bw']=b.dismissal_type.isin(['Bowled','Caught','Hit Wicket','LBW','Stump']).astype(int)
    b['out']= (b.is_wicket & b.dismissed_player_id.eq(b.striker_id)).astype(int)
    grp=b.groupby(['match_id','innings'],sort=False)
    b['score_before']=grp.team_runs.cumsum()-b.team_runs
    b['balls_used']=grp.legal.cumsum()-b.legal.astype(int)
    b['lost']=grp.is_wicket.cumsum()-b.is_wicket.astype(int)
    b['balls_left']=120-b.balls_used; b['wickets_left']=10-b.lost
    b['phase']=np.select([b.balls_used.lt(36),b.balls_used.lt(90)],['Powerplay','Middle'],default='Death')
    totals=grp.agg(total=('team_runs','sum'),wickets=('is_wicket','sum'),legal=('legal','sum'),rows=('runs','size')).reset_index()
    first=totals[totals.innings.eq(1)].set_index('match_id').total
    b['target']=b.match_id.map(first)+1
    b['runs_needed']=b.target-b.score_before
    overs=b.groupby(['match_id','innings','overid']).legal.sum().rename('legal').reset_index()
    overs['last']=overs.groupby(['match_id','innings']).overid.transform('max')
    malformed=overs[(overs.overid.lt(overs['last']) & overs.legal.ne(6))|overs.legal.gt(6)]
    audit['non_six_ball_interior_overs']=malformed.to_dict('records')
    audit['retired_or_unknown_nonwickets']=int((b.dismissed_player_id.notna()&~b.is_wicket).sum())
    audit['zero_speed_deliveries']=int(b.bowl_speed.eq(0).sum())
    # Validate result margins independent of delivery state. Metadata contains no scorecard totals.
    checks=[]
    for row in m.itertuples():
        q=totals[totals.match_id.eq(row.match_id)].set_index('innings')
        if not {1,2}.issubset(q.index) or pd.notna(row.revised_target): continue
        r=re.search(r'Won by (\d+) runs?',row.result,re.I)
        w=re.search(r'Won by (\d+) Wickets?',row.result,re.I)
        if r: checks.append({'match_id':row.match_id,'type':'runs','expected':int(r[1]),'reconstructed':int(q.loc[1,'total']-q.loc[2,'total'])})
        elif w: checks.append({'match_id':row.match_id,'type':'wickets','expected':int(w[1]),'reconstructed':int(10-q.loc[2,'wickets'])})
    audit['margin_checks']={'checked':len(checks),'failed':[x for x in checks if x['expected']!=x['reconstructed']]}
    audit['spotchecks']=totals[totals.match_id.isin([13511,13512,21586,14130,41509])].to_dict('records')
    # Whole matches excluded if final revision timing is absent: no retrospective DLS leakage.
    masks=[('Other T20 competitions',b.league.eq('Other T20')),
           ('Super Over innings 3/4',b.innings.gt(2)),
           ('Abandoned or no result',b.result.str.contains('No Result|Abandoned',case=False)),
           ('Any revised target/length or DLS result',b[['first_inn_revised_overs','second_inn_revised_overs','revised_target']].notna().any(axis=1)|b.result.str.contains(r'D/L|DLS',case=False)),
           ('Unresolved result-margin mismatch',b.match_id.isin([x['match_id'] for x in audit['margin_checks']['failed']])),
           ('Incomplete/irregular interior over',b.match_id.isin(malformed.match_id)),
           ('Unclassifiable extras encoding',b.match_id.isin(b[(b.extras_type.isna()&(b.extras1_runs.gt(0)|b.extras_2_runs.gt(0)))|(b.extras_type.eq('legbyes')&b.runs.gt(0))].match_id)),
           ('Invalid pre-ball state',b.balls_left.le(0)|b.wickets_left.le(0)|(b.innings.eq(2)&b.runs_needed.le(0))),
           ('Future match date',b.match_date.gt(AS_OF))]
    keep=pd.Series(True,index=b.index); exc=[]
    for label,mask in masks:
        e=keep&mask;exc.append({'reason':label,'deliveries':int(e.sum()),'matches':int(b.loc[e,'match_id'].nunique())});keep &= ~mask
    audit['exclusions_sequential']=exc
    b=b[keep].copy().reset_index(drop=True)
    audit['included']={'deliveries':len(b),'matches':b.match_id.nunique(),'start':b.match_date.min(),'end':b.match_date.max()}
    audit['included_coverage']=b.groupby(['league','season']).agg(deliveries=('match_id','size'),matches=('match_id','nunique')).reset_index().to_dict('records')
    return b,audit

def pressure(b):
    # Only strictly earlier calendar years train situational scoring expectations.
    b['base_rpb']=0.;b['expected_so_far']=0.
    defaults={'Powerplay':1.25,'Middle':1.25,'Death':1.65}
    for league in ['IPL','T20I']:
        for year in sorted(b.year.unique()):
            history=b[b.year.lt(year)&b.league.eq(league)]
            rates={p:(history.loc[history.phase.eq(p),'team_runs'].sum()+300*defaults[p])/(history.loc[history.phase.eq(p),'legal'].sum()+300) for p in defaults}
            ix=b.league.eq(league)&b.year.eq(year); used=b.loc[ix,'balls_used']
            b.loc[ix,'base_rpb']=b.loc[ix,'phase'].map(rates)
            b.loc[ix,'expected_so_far']=np.minimum(used,36)*rates['Powerplay']+np.minimum(np.maximum(used-36,0),54)*rates['Middle']+np.maximum(used-90,0)*rates['Death']
    b['resource_rate']=b.base_rpb*(1-.06*np.maximum(b.lost-2,0)).clip(.58,1)
    b['demand_ratio']=(b.runs_needed/b.balls_left)/b.resource_rate
    urgency=1-b.balls_left/120; depletion=(b.lost/7).clip(0,1)
    deficit=((b.expected_so_far-b.score_before)/(15+.2*b.expected_so_far)).clip(0,1)
    first=.4*urgency+.35*deficit+.25*depletion
    chase=.45*(b.demand_ratio/1.4).clip(0,1)+.35*urgency+.2*depletion
    live=b.demand_ratio.between(.65,1.8)&b.runs_needed.gt(0)
    b['pressure']=np.where(b.innings.eq(1),first,np.where(live,chase,0))
    return b

def peer_residual(d,category,high):
    # Hierarchical leave-one-match-out ordinary peers; residuals are performance, not win probability.
    d=d.copy();d['high']=high
    if category=='batters':
        d=d[~d.extras_type.eq('wide')].copy();d['pid']=d.striker_id;d['name']=d.striker_name
        d['role']=np.select([d.batting_order.le(3),d.batting_order.le(6)],['1-3','4-6'],default='7+')
        d['opp']=d.bowling_team_id;d['run']=d.runs.astype(float);d['wicket']=d['out']; sign=1.;rw=.65;ww=.35
    else:
        d['pid']=d.bowler_id;d['name']=d.bowler_name;d['role']=d.pace_or_spin;d['opp']=d.batting_team_id
        d['run']=d.charged.astype(float);d['wicket']=d.bw;sign=-1.;rw=.6;ww=.4
    d['resource']=pd.cut(d.lost,[-1,2,5,10],labels=['0-2','3-5','6+']).astype(str)
    # Every peer outcome excludes all rows from the current match, including ordinary rows.
    def loo(keys,col):
        a=d.assign(v=np.where(~d.high,d[col],0),n=(~d.high).astype(int))
        g=a.groupby(keys,observed=True);h=a.groupby(keys+['match_id'],observed=True)
        return g.v.transform('sum')-h.v.transform('sum'),g.n.transform('sum')-h.n.transform('sum')
    for col,default in [('run',1.35),('wicket',.055)]:
        s,n=loo(['phase','role'],col);p=(s+300*default)/(n+300)
        for keys,k in [(['league','season','phase','innings','role','resource'],150),(['league','season','phase','innings','role','resource','opp'],250)]:
            s,n=loo(keys,col);p=(s+k*p)/(n+k)
        d['peer_'+col]=p
    d['run_component']=sign*rw*(d.run-d.peer_run)/1.7
    d['wicket_component']=-sign*ww*(d.wicket-d.peer_wicket)/.22
    d['utility']=d.run_component+d.wicket_component
    return d

def fit(d,category,bootstrap=False):
    min_n,min_m,min_o=(120,12,200) if category=='batters' else (180,15,240)
    o=d[~d.high].groupby(['pid','phase']).utility.agg(['sum','count'])
    o['own']=o['sum']/(o['count']+100)
    d=d.join(o['own'],on=['pid','phase']);d['own']=d['own'].fillna(0)
    d['own_run_expected']=d.peer_run
    p=d[d.high].copy()
    nordinary=d[~d.high].groupby('pid').size()
    rows=[]
    for pid,q in p.groupby('pid'):
        if int(pid) in EXCLUSIONS: continue
        n=len(q); matches=q.match_id.nunique(); no=int(nordinary.get(pid,0))
        if n<min_n or matches<min_m or no<min_o: continue
        alpha=n/(n+150); A=alpha*q.utility.mean(); O=q['own'].mean()
        mm=q.groupby('match_id').utility.mean(); phase=q.phase.value_counts().idxmax()
        raw_score=50+20*(A-.2*O)
        rows.append({'player_id':int(pid),'name':q.name.mode().iloc[0],'role':q.role.mode().iloc[0],
            'pressure_deliveries':n,'pressure_legal_balls':int(q.legal.sum()),'pressure_matches':matches,'ordinary_deliveries':no,
            'absolute_pressure_index':50+20*A,'own_ordinary_index':50+20*O,'change':20*(A-O),'raw_score':raw_score,
            'run_component':20*alpha*q.run_component.mean(),'wicket_component':20*alpha*q.wicket_component.mean(),
            'runs':q.run.sum(),'wickets':q.wicket.sum(),'pressure_run_rate':6*q.run.sum()/max(q.legal.sum(),1) if category=='bowlers' else 100*q.run.mean(),
            'dismissal_pct':100*q.wicket.mean(),'peer_run_rate':6*q.peer_run.sum()/max(q.legal.sum(),1) if category=='bowlers' else 100*q.peer_run.mean(),
            'peer_wicket_pct':100*q.peer_wicket.mean(),'positive_match_pct':100*mm.gt(0).mean(),'match_sd':float(20*mm.std()),
            'dominant_phase':phase,'ipl_pressure_deliveries':int(q.league.eq('IPL').sum()),'shrinkage':alpha})
    r=pd.DataFrame(rows)
    if len(r)==0: return r,d
    # Joint match block bootstrap: same multiplicity for every player and both pressure/ordinary.
    if bootstrap:
        ids=np.sort(d.match_id.unique());rng=np.random.default_rng(SEED)
        weights=rng.multinomial(len(ids),np.full(len(ids),1/len(ids)),size=BOOT).T
        players=r.player_id.tolist();dist=np.empty((BOOT,len(players)))
        for j,pid in enumerate(players):
            z=d[d.pid.eq(pid)];phases=['Powerplay','Middle','Death']
            def mat(high,col):
                v=z[z.high.eq(high)].groupby(['match_id','phase'])[col].sum().unstack('phase').reindex(index=ids,columns=phases).fillna(0).values
                return weights.T@v
            z=z.copy();z['one']=1
            pn=mat(True,'one');ps=mat(True,'utility');on=mat(False,'one');os=mat(False,'utility')
            total=pn.sum(1);A=ps.sum(1)/(total+150);O=((os/(on+100))*pn).sum(1)/np.maximum(total,1)
            dist[:,j]=50+20*(A-.2*O)
        se=dist.std(0,ddof=1);r['uncertainty_se']=se;r['pressure_score']=r.raw_score-.35*se
        scored=dist-.35*se[None,:]
        ranks=np.argsort(np.argsort(-scored,axis=1),axis=1)+1
        r['ci_low']=np.quantile(scored,.025,axis=0);r['ci_high']=np.quantile(scored,.975,axis=0)
        r['top10_probability']=(ranks<=10).mean(0);r['rank_low']=np.quantile(ranks,.025,axis=0);r['rank_high']=np.quantile(ranks,.975,axis=0)
    else:
        # Match-cluster delta SE; used only in exploratory scenarios for speed.
        se=[]
        for row in r.itertuples():
            q=p[p.pid.eq(row.player_id)];s=q.groupby('match_id').utility.agg(['sum','count']);mean=q.utility.mean()
            v=((s['sum']-mean*s['count'])**2).sum()*len(s)/(len(s)-1)/len(q)**2
            se.append(20*row.shrinkage*np.sqrt(v))
        r['uncertainty_se']=se;r['pressure_score']=r.raw_score-.35*r.uncertainty_se
    r=r.sort_values(['pressure_score','pressure_deliveries'],ascending=False).reset_index(drop=True);r['rank']=np.arange(1,len(r)+1)
    return r,d

def main():
    a=argparse.ArgumentParser();a.add_argument('--data-dir',type=Path,required=True);args=a.parse_args();OUT.mkdir(exist_ok=True)
    b,audit=load_data(args.data_dir);b=pressure(b);dump('audit.json',audit)
    eligibility={'as_of':AS_OF,'policy':'Rank all supplied players who meet the performance sample rules, including retired players. Retirement, franchise retention and auction availability do not exclude historical candidates.',
                 'policy_evidence':'data/reference/historical_eligibility_policy.json',
                 'excluded':[{'player_id':pid,**record} for pid,record in EXCLUSIONS.items()]}
    dump('eligibility.json',eligibility)
    pd.DataFrame(audit['coverage']).to_csv(OUT/'competition_coverage.csv',index=False)
    pd.DataFrame(audit['included_coverage']).to_csv(OUT/'included_seasons.csv',index=False)
    allout={};rob={};details={};scenarios={}
    for cat in ['batters','bowlers']:
        print('Fitting',cat,flush=True)
        d=peer_residual(b,cat,b.pressure.ge(.62));r,d=fit(d,cat,True)
        assert len(r)>=10
        r.to_csv(OUT/(cat+'_all.csv'),index=False)
        allout[cat]=r.head(10).to_dict('records');details[cat]=[]
        for pid in r.player_id:
            q=d[d.pid.eq(pid)];rec={'player_id':pid,'name':q.name.mode().iloc[0],'breakdowns':[]}
            for field in ['phase','league']:
                for value,z in q.groupby(field):
                    h=z[z.high];o=z[~z.high]
                    if len(h)<30 or len(o)<30 or h.match_id.nunique()<4: continue
                    rec['breakdowns'].append({'dimension':field,'value':value,'pressure_n':len(h),'ordinary_n':len(o),'matches':h.match_id.nunique(),
                        'pressure_index':50+20*h.utility.sum()/(len(h)+150),'ordinary_index':50+20*h['own'].mean(),
                        'pressure_run_metric':(100*h.run.mean() if cat=='batters' else 6*h.run.sum()/h.legal.sum()),
                        'ordinary_run_metric':(100*o.run.mean() if cat=='batters' else 6*o.run.sum()/o.legal.sum())})
            rec.update(r[r.player_id.eq(pid)].iloc[0].to_dict());details[cat].append(rec)
        rob[cat]={};scenarios[cat]={}
        for label,threshold,ipl in [('Broader pressure',.57,False),('Stricter pressure',.67,False),('IPL only',.62,True),('Scoring-heavy weights',.62,False),('Wicket-heavy weights',.62,False)]:
            x=b[b.league.eq('IPL')].copy() if ipl else b
            dd=peer_residual(x,cat,x.pressure.ge(threshold))
            if label in ['Scoring-heavy weights','Wicket-heavy weights']:
                rw,ww=(.75,.25) if label.startswith('Scoring') else (.5,.5)
                oldrw,oldww=(.65,.35) if cat=='batters' else (.6,.4)
                dd['utility']=dd.run_component*rw/oldrw+dd.wicket_component*ww/oldww
            rr,_=fit(dd,cat,True)
            scenarios[cat][label]=rr.to_dict('records')
            top=set(rr.head(10).player_id);official=set(r.head(10).player_id)
            common=r[['player_id','rank']].merge(rr[['player_id','rank']],on='player_id')
            rob[cat][label]={'threshold':threshold,'eligible':len(rr),'overlap':len(top&official),'spearman':spearmanr(common['rank_x'],common['rank_y']).statistic,
                'top10':[x for x in rr.head(10).name], 'official_ranks':{str(pid):int(rr.set_index('player_id').loc[pid,'rank']) if pid in set(rr.player_id) else None for pid in r.head(10).player_id}}
        # Per-player ordinary raw metrics are descriptive; adjusted baseline is the index.
        for rec in details[cat]:
            q=d[(d.pid.eq(rec['player_id']))&~d.high]
            rec['ordinary_run_metric']=100*q.run.mean() if cat=='batters' else 6*q.run.sum()/q.legal.sum()
            rec['ordinary_dismissal_pct']=100*q.wicket.mean()
        print(r.head(12)[['rank','name','pressure_score','absolute_pressure_index','change','pressure_deliveries','pressure_matches','top10_probability']].to_string(index=False),flush=True)
    dump('rankings.json',allout);dump('players.json',details);dump('robustness.json',rob);dump('scenarios.json',scenarios)
    for cat in allout: pd.DataFrame(allout[cat]).to_csv(OUT/(cat+'_top10.csv'),index=False)
    txt='SupeRR Selector Season 2 - Round 1\nOfficial rankings | analysis as of 13 November 2026\n\n'
    for cat in allout:
        txt+=cat.upper()+'\n'+'\n'.join(f'Rank {i+1}: {r["name"]}' for i,r in enumerate(allout[cat]))+'\n\n'
    txt+='Names are exact source-data labels, identified by player_id in rankings.json.\nUnstop dropdown options were not supplied or accessible; spelling and selection eligibility require manual verification.\nRankings measure historical performance, not confirmed IPL 2027 auction eligibility or availability.\n'
    (ROOT/'unstop_rankings.txt').write_text(txt)
    # Aggregate pressure diagnostics, no raw records.
    diag=b.assign(high=b.pressure.ge(.62)).groupby(['league','innings','phase']).agg(deliveries=('match_id','size'),pressure=('high','sum'),mean_pressure=('pressure','mean')).reset_index()
    dump('pressure_diagnostics.json',diag.to_dict('records'))
    print('Complete',audit['included'],flush=True)

if __name__=='__main__': main()
