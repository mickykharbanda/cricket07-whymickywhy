"""Freeze official 2026 IPL squad facts and official crest/kit-reference assets."""
import concurrent.futures
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'mods/modern-2026/sources';OUT.mkdir(parents=True,exist_ok=True)
SLUGS=['chennai-super-kings','delhi-capitals','gujarat-titans','kolkata-knight-riders','lucknow-super-giants','mumbai-indians','punjab-kings','rajasthan-royals','royal-challengers-bengaluru','sunrisers-hyderabad']
def fetch(slug):
    url=f'https://www.iplt20.com/api/bff/cms/teams/{slug}?tab=squad&season=2026'
    dest=OUT/(slug+'.json')
    subprocess.run(['curl','-fLs','--retry','2','--max-time','25',url,'-o',str(dest)],check=True)
    j=json.loads(dest.read_text())['data'];players=j['squad']['players']
    assert len(players)>=11,(slug,len(players))
    j['sourceUrl']=url;j['sourceSeason']='2026'
    crest=j['teamCrestUrl'];subprocess.run(['curl','-fLs','--max-time','15',crest,'-o',str(OUT/(slug+'-crest.svg'))],check=True)
    reference=next((p for p in players if p.get('isCaptain')),players[0])
    subprocess.run(['curl','-fLs','--max-time','15',reference['imageUrl'],'-o',str(OUT/(slug+'-kit-reference.png'))],check=True)
    dest.write_text(json.dumps(j,indent=2)+'\n')
    return slug,len(players)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    for item in pool.map(fetch,SLUGS):print(*item)
