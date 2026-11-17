"""Package code, public references and aggregates only; no raw records or uploads."""
from pathlib import Path
import json,hashlib,zipfile
ROOT=Path(__file__).resolve().parents[1]
files=[ROOT/n for n in ['README.md','requirements.txt','.gitignore','rr_auction_dashboard.html','unstop_rankings.txt']]
for folder,suffixes in [('analysis',{'.py','.html','.css'}),('data/reference',{'.csv','.json','.md','.png','.svg'}),('output',{'.csv','.json','.pdf'})]:
 files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in suffixes and not any(x.startswith('.') or x=='__pycache__' for x in p.relative_to(ROOT/folder).parts))
files=sorted(set(files));names=[p.relative_to(ROOT).as_posix() for p in files]
raw={'ball_by_ball.csv','competition_team_player_mapping.csv','competitions.csv','matches.csv','playing_eleven.csv','teams.csv'}
assert not any(Path(n).name in raw or n.startswith('tmp/') for n in names)
manifest={n:hashlib.sha256(p.read_bytes()).hexdigest() for p,n in zip(files,names)}
mp=ROOT/'submission_manifest.json';mp.write_text(json.dumps(manifest,indent=2)+'\n');files.append(mp)
with zipfile.ZipFile(ROOT/'rr_submission_bundle.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in files:
  info=zipfile.ZipInfo(p.relative_to(ROOT).as_posix(),date_time=(2026,11,13,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
  z.writestr(info,p.read_bytes())
with zipfile.ZipFile(ROOT/'rr_submission_bundle.zip') as z:
 assert z.testzip() is None
 for n,digest in manifest.items():assert hashlib.sha256(z.read(n)).hexdigest()==digest
print(f'Packaged {len(files)} files; SHA-256 manifest verified; no raw input, temporary research or system metadata included.')
