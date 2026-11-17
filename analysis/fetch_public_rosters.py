"""Fetch public IPL roster data only. Never opens proprietary files or transmits player queries."""
import argparse,json,hashlib,urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
TEAMS={'CSK':'chennai-super-kings','DC':'delhi-capitals','GT':'gujarat-titans','KKR':'kolkata-knight-riders','LSG':'lucknow-super-giants','MI':'mumbai-indians','PBKS':'punjab-kings','RR':'rajasthan-royals','RCB':'royal-challengers-bengaluru','SRH':'sunrisers-hyderabad'}
ROOT=Path(__file__).resolve().parents[1]
def fetch(item):
 code,slug=item;url=f'https://www.iplt20.com/api/bff/cms/teams/{slug}?tab=squad'
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
 raw=urllib.request.urlopen(req,timeout=40).read();obj=json.loads(raw);data=obj['data'];rows=data['squad']['players']
 if len(rows)<18:raise ValueError(f'Incomplete squad: {code}, {len(rows)}')
 clean=[{k:p.get(k) for k in ['name','externalId','slug','role','country','countryCode']} for p in rows]
 print(code,len(clean),flush=True)
 return code,{'team':data['title'],'season':2026,'source_url':url,'page_url':f'https://www.iplt20.com/teams/{slug}/squad','source_type':'official','announcement_date':'unknown','verification_date':ARGS.as_of,'response_sha256':hashlib.sha256(raw).hexdigest(),'players':clean}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--as-of',default='2026-11-13');ARGS=a.parse_args()
 with ThreadPoolExecutor(max_workers=4) as pool:result=dict(pool.map(fetch,TEAMS.items()))
 out=ROOT/'data/reference/public_rosters_2026.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2))
 print('Saved public facts only:',out)
