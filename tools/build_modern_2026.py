"""Reversible 2026 expansion using secondary teams; preserve the OG senior squads."""
import base64,copy,hashlib,io,json,re,struct,unicodedata,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image,ImageDraw
import cairosvg
from big_archive import entries,read,decompress
from fsh import decode,replace_kit_image,replace_logo_images
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'mods/modern-2026';SRC=OUT/'sources'
ARCHIVE=ROOT/'game/Data/data.gob';ES={e[0]:e for e in entries(ARCHIVE)}
with ARCHIVE.open('rb') as stream:INDEX=stream.read(157696)
PLAN=json.loads((OUT/'team-plan.json').read_text());RESOURCES=[]
CDF='113964e05e69ab31d264fb8f15c58e5c.cdf'

def resource(name,data):
    assert name in ES,name
    e=ES[name];position=INDEX.index(name.encode()+b'\0')-8
    assert struct.unpack_from('>II',INDEX,position)==e[1:]
    RESOURCES.append(dict(resource=name,indexPosition=position,originalEntry=list(e[1:]),data=data))

def load(name):return decompress(read(ARCHIVE,ES[name]))
def hashed(path,ext):return hashlib.md5(path.encode()).hexdigest()+ext

def norm(name):
    name={'Mahendra Singh Dhoni':'MS Dhoni','Mitch Marsh':'Mitchell Marsh','Mitch Santner':'Mitchell Santner','Matt Short':'Matthew Short','Mitch Owen':'Mitchell Owen','Thangarasu Natarajan':'T Natarajan'}.get(name,name)
    return unicodedata.normalize('NFKD',name).encode('ascii','ignore').decode()
def short_name(name):
    name=norm(name)
    if name.startswith('MS '):return 'MS.'+name[3:]
    if name.startswith('KL '):return 'KL.'+name[3:]
    words=name.split();short=''.join(w[0] for w in words[:-1])+'.'+words[-1]
    assert len(short)<16,(name,short)
    return short

# Proxy templates preserve the original game's playable DNA and role bits. They
# are game-balancing defaults, not claims about actual 2026 statistics or faces.
LEFT={'Axar Patel','Ishan Kishan','Shivam Dube','Yashasvi Jaiswal','Vaibhav Sooryavanshi','Sai Sudharsan','Abhishek Sharma','Ravindra Jadeja','Krunal Pandya','Devdutt Padikkal','Venkatesh Iyer','Rinku Singh','Nitish Rana','David Miller','Tilak Varma','Sherfane Rutherford','Nicholas Pooran','Rishabh Pant','Travis Head','Shimron Hetmyer','Sam Curran','Marco Jansen','Akeal Hosein','Mitchell Santner','Rachin Ravindra','Quinton de Kock','Ryan Rickelton','Abishek Porel','Washington Sundar','Nehal Wadhera','Cooper Connolly','Kamindu Mendis','Shahbaz Ahmed'}
LEFT_PACE={'Arshdeep Singh','Trent Boult','Mitchell Starc','Khaleel Ahmed','Mohsin Khan','Jaydev Unadkat','Yash Dayal','T Natarajan','Nandre Burger','Luke Wood','Marco Jansen','Sam Curran','Arjun Tendulkar','Mukesh Choudhary'}
SPIN={'Kuldeep Yadav','Rashid Khan','Ravi Bishnoi','Yuzvendra Chahal','Varun Chakaravarthy','Suyash Sharma','Noor Ahmad','Rahul Chahar','Shreyas Gopal','Mayank Markande','Digvesh Singh Rathi','Harsh Dubey','Zeeshan Ansari','Vignesh Puthur','AM Ghazanfar'}
OFF={'Sunil Narine','Washington Sundar','Will Jacks','Naman Dhir','Aiden Markram','Glenn Phillips','Liam Livingstone'}
LA_SPIN={'Axar Patel','Ravindra Jadeja','Krunal Pandya','Mitchell Santner','Akeal Hosein','Shahbaz Ahmed','Sai Kishore','Manav Suthar','Manimaran Siddharth','Swapnil Singh'}

def donor(player):
    name=norm(player['name']);role=player.get('role','batsman')
    if player.get('isWicketKeeper') or name in {'Phil Salt','Heinrich Klaasen','MS Dhoni','KL Rahul','Sanju Samson'}:return 552 if name in LEFT else 545
    if name in LA_SPIN:return 554
    if name in OFF:return 530
    if name in SPIN:return 539
    if name in LEFT_PACE:return 562
    if role=='bowler':return 553
    if role=='allrounder':return 547
    return 534 if name in LEFT else 525

def svg_image(svg,size):
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(),output_width=size[0],output_height=size[1]))).convert('RGBA')

def crest(team):
    file=SRC/(team['slug']+'-crest.svg')
    if file.exists():return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=file.read_bytes(),output_width=128,output_height=128))).convert('RGBA')
    # India roundel is drawn as a new vector badge, separate from the OG texture.
    return svg_image('<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128"><circle cx="64" cy="64" r="60" fill="#193779" stroke="#f3c848" stroke-width="7"/><circle cx="64" cy="64" r="38" fill="none" stroke="#f3c848" stroke-width="4"/><text x="64" y="74" text-anchor="middle" font-family="sans-serif" font-size="25" fill="white">IND</text></svg>',(128,128))

def vector_texture(team,kind):
    colour=team['colour'];accent=team['accent'];slug=team['slug'];sponsor=team['sponsor']
    badge=crest(team);buf=io.BytesIO();badge.save(buf,format='PNG');image='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()
    # Match the original game's fixed atlas islands, using deterministic SVG
    # panels and native FSH output. No original India bitmap is overwritten.
    if kind=='kit1':
        w=h=512;parts=[f'<rect width="512" height="512" fill="{colour}"/>']
        # The top two islands are torso back/front; their longitudinal direction
        # is sideways in this legacy UV layout. Lower islands are trousers.
        if slug=='lucknow-super-giants':
            parts += [f'<path d="M{x} 0l45 220h-24L{x-24} 0z" fill="{accent}"/>' for x in range(25,520,64)]
        elif slug=='punjab-kings':
            parts += [f'<path d="M0 0h82l18 220H0zM430 0h82v220h-100z" fill="{accent}"/>']
        elif slug=='royal-challengers-bengaluru':
            parts += [f'<path d="M0 155h512v357H0z" fill="{accent}"/>']
        elif slug=='rajasthan-royals':
            parts += [f'<path d="M0 125l512 25v362H0z" fill="{accent}"/>']
        else:
            parts += [f'<path d="M0 5h512v12H0zM0 196h512v14H0zM0 222h14v290H0zM356 222h13v290h-13z" fill="{accent}"/>']
        # Seam and fabric shading are code-native, not painted over old logos.
        parts += ['<rect width="512" height="512" fill="url(#cloth)" opacity=".22"/>',
                  '<path d="M0 220H512M380 220V512" stroke="#001329" stroke-opacity=".4" stroke-width="3"/>',
                  f'<path d="M240 75q-28 32 0 66l15-13q-18-22 0-42z" fill="{accent}"/>',
                  f'<g transform="translate(365 110) rotate(-90)"><image href="{image}" x="-84" y="-60" width="40" height="40"/><text x="5" y="7" font-family="Arial,sans-serif" font-weight="bold" font-size="{17 if len(sponsor)>10 else 24}" text-anchor="middle" fill="white">{sponsor}</text><text x="3" y="31" text-anchor="middle" fill="white" font-family="Arial" font-size="12">{team["abbr"]}</text></g>',
                  '<rect x="382" y="356" width="130" height="156" fill="#d5d9df"/><path d="M386 424h110v40H386z" fill="#20242a"/><path d="M400 369l50 55m-40-57 50 55m-38-56 49 55" stroke="white" stroke-width="6"/>']
    else:
        w=h=256 if kind!='helm' else 128
        parts=[f'<rect width="{w}" height="{h}" fill="{colour}"/>',f'<rect width="{w}" height="{h}" fill="url(#cloth)" opacity=".2"/>']
        if kind in ['kit2','kit3']:
            parts += [f'<path d="M82 0h12v256H82zM232 0h12v256h-12z" fill="{accent}"/>']
            parts += [f'<path d="M95 {y}H230" stroke="white" stroke-opacity=".24" stroke-width="3"/>' for y in range(30,250,15)]
            parts += ['<rect width="74" height="256" fill="#e1e3e6"/><path d="M0 100h74v8H0zM0 170h74v8H0z" fill="#333"/>']
        elif kind=='accs':
            parts += [f'<image href="{image}" x="170" y="8" width="42" height="42"/><image href="{image}" x="165" y="153" width="38" height="38"/>',f'<path d="M0 80h256v8H0z" fill="{accent}"/>']
        else:
            parts += [f'<image href="{image}" x="48" y="38" width="38" height="38"/>']
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}"><defs><linearGradient id="cloth" x2="0.8" y2="1"><stop stop-color="white"/><stop offset=".25" stop-color="#131b2b"/><stop offset=".38" stop-color="white"/><stop offset=".65" stop-color="#091326"/><stop offset="1" stop-color="white"/></linearGradient></defs>'+''.join(parts)+'</svg>'
    folder=OUT/'kits'/slug;folder.mkdir(parents=True,exist_ok=True);(folder/(kind+'.svg')).write_text(svg)
    im=svg_image(svg,(w,h));im.save(folder/(kind+'.png'));return im

def build():
    original=load(CDF);data=bytearray(original)
    protected=set()
    preserved=list(range(44))+list(range(55,63))
    for slot in preserved:protected.update(struct.unpack_from('<20H',original,432004+2808*slot))
    # All original India players are protected, including the reserves beyond XI.
    protected_rows=set(range(524,565))
    for row in range(1200):
        if struct.unpack_from('<H',original,row*360+4)[0] in protected:protected_rows.add(row)
    free=[r for r in range(1,1199) if r not in protected_rows]
    free.sort(key=lambda r:(bool(original[r*360+8:r*360+24].split(b'\0')[0]),-r))
    original_ids={struct.unpack_from('<H', original,r*360+4)[0] for r in range(1200)}
    new_ids=iter(i for i in range(30000,32768) if i not in original_ids)
    allocated={};player_details=[];team_details=[]
    info=ET.fromstring(load('be2970b0ada8e42cf891ce60ffe69575.xml'))
    manager=ET.fromstring(load('730eef3fd7726e43de955f21083ab000.xml'))
    legacy_info=ET.fromstring(load('49ad277eb4663535abe0d4b1ec726023.xml'))
    for team in PLAN:
        if team['slug']=='india-odi-2026':
            names=team['players'].split('|');captain=team['captain'];title='India ODI 2026'
            source='https://www.bcci.tv/news/article/indias-odi-and-test-squads-for-new-zealand-tour-announced'
            # Official IPL player flags are reused for players shared with ODI.
            pool={norm(p['name']):p for f in SRC.glob('*.json') for p in json.loads(f.read_text())['squad']['players']}
            chosen=[]
            for name in names:
                player=copy.deepcopy(pool.get(norm(name),dict(name=name,role='batsman')));player['name']=name
                if name=='KL Rahul':player['isWicketKeeper']=True
                chosen.append(player)
        else:
            src=json.loads((SRC/(team['slug']+'.json')).read_text());pool={p['name']:p for p in src['squad']['players']}
            chosen=[copy.deepcopy(pool[n]) for n in team['players'].split('|')];title=src['title'];source=src['sourceUrl']
            captain=next(p['name'] for p in src['squad']['players'] if p.get('isCaptain'))
        ids=[];numbers=[]
        for player in chosen:
            name=norm(player['name'])
            if name not in allocated:
                row=free.pop(0);template=donor(player);pid=next(new_ids)
                start=row*360+4;donor_start=template*360+4
                data[start:start+360]=original[donor_start:donor_start+360]
                struct.pack_into('<HH',data,start,pid,65535)
                label=short_name(name).encode();data[start+4:start+20]=label.ljust(16,b'\0')
                # New players do not inherit a 2006 player's international stats.
                data[start+20:start+100]=bytes(80)
                allocated[name]=(pid,row)
                player_details.append(dict(name=name,displayName=label.decode(),id=pid,row=row,templateRow=template,role=player.get('role'),isWicketKeeper=player.get('isWicketKeeper',False)))
            ids.append(allocated[name][0]);numbers.append(int(player.get('jerseyNumber') or 0)%100)
        off=432004+team['slot']*2808;template_off=432004+13*2808
        # Team records begin 24 bytes before the 20-player selection array.
        data[off-24:off-24+2808]=original[template_off-24:template_off-24+2808]
        data[off-24:off-4]=bytes(numbers+[0]*(20-len(numbers)))
        struct.pack_into('<20H',data,off,*(ids+[65535]*(20-len(ids))))
        struct.pack_into('<I',data,off+40,team['slot'])
        struct.pack_into('<H',data,off+46,allocated[norm(captain)][0])
        node=next(t for t in info.findall('team') if int(t.get('Index'))==team['slot'])
        old_title=node.get('TeamName');node.set('TeamName','Royal Challengers' if team['abbr']=='RCB' else title);node.set('TeamNameShort',team['short']);node.set('Abbreviation',team['abbr']);node.set('StandardOfCricket','3')
        mgr=next(t for t in manager.findall('./teams/team') if int(t.get('id'))==team['slot']);mgr.set('name',title)
        for kit in mgr.findall('kit'):
            kit.set('namecolour','#FFFFFF');kit.set('numbercolour','#FFFFFF')
        for t in legacy_info.iter('team'):
            if t.get('Abbreviation','').lower()==team['code']:
                t.set('TeamName',title);t.set('TeamNameShort',team['short'])
        team_details.append(dict(name=title,slug=team['slug'],slot=team['slot'],replaces=old_title,code=team['code'],captain=captain,source=source,selectedPlayers=[norm(p['name']) for p in chosen]))
    assert len(data)==len(original)
    for row in protected_rows:
        start=row*360+4;assert data[start:start+360]==original[start:start+360],f'OG player overwritten: {row}'
    for slot in preserved:
        start=432004+2808*slot-24
        assert data[start:start+2808]==original[start:start+2808],f'OG squad overwritten: {slot}'
    resource(CDF,bytes(data))
    for filename,xml in [('be2970b0ada8e42cf891ce60ffe69575.xml',info),('730eef3fd7726e43de955f21083ab000.xml',manager),('49ad277eb4663535abe0d4b1ec726023.xml',legacy_info)]:resource(filename,ET.tostring(xml,encoding='utf-8',xml_declaration=True))
    for team in PLAN:
        for kind,suffix in [('kit1','colouredkit1'),('kit2','colouredkit2'),('kit3','colouredkit3'),('accs','colouredaccessories'),('helm','helm')]:
            filename=hashed('teams/'+team['code']+'/'+suffix,'.fsh');old=load(filename);im=vector_texture(team,kind)
            resource(filename,replace_kit_image(old,im))
    logo_map=json.loads((OUT/'logo-map.json').read_text())
    for team in PLAN:
        for filename in logo_map[str(team['slot'])]:resource(filename,replace_logo_images(load(filename),crest(team)))
    previous=[]
    if (OUT/'manifest.json').exists():
        old=json.loads((OUT/'manifest.json').read_text())
        previous=old.get('previousLayouts',[])+[dict(size=old['size'],resources=[dict(resource=r['resource'],offset=r['offset'],size=r['size']) for r in old['resources']])]
        previous=previous[-3:]
    payload=bytearray();manifest=[]
    for r in RESOURCES:
        content=r.pop('data');r.update(offset=len(payload),size=len(content),sha256=hashlib.sha256(content).hexdigest());payload+=content;manifest.append(r)
    (OUT/'modern-pack.bin').write_bytes(payload)
    (OUT/'manifest.json').write_text(json.dumps(dict(id='modern-2026-v1',file='modern-pack.bin',originalSize=ARCHIVE.stat().st_size,size=len(payload),sha256=hashlib.sha256(payload).hexdigest(),resources=manifest,previousLayouts=previous,teams=team_details,players=player_details,preservedTeamSlots=preserved,protectedPlayerRows=sorted(protected_rows),kitNote='Fan recreations from official 2026 player-shirt references; not official downloadable game skins.',ratingNote='Playable proxy attributes and generic faces; career stats reset; not official ratings.'),indent=2)+'\n')
    print(f'Built {len(PLAN)} teams, {len(allocated)} separate players, {len(RESOURCES)} resources, {len(payload)/1e6:.1f} MB. {len(protected_rows)} OG player records and {len(preserved)} OG squads verified unchanged.')

if __name__=='__main__':build()
