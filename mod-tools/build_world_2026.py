"""World 2026 pack: every 2026 national side, the ten IPL sides and five dream XIs.

A third, separate roster beside Original and modern-2026. It is applied to the browser/app cache
the same reversible way (append + repoint), so the source archive is never touched.

What it replaces, only while the pack is applied:
  - eighteen international slots get their latest 2026 ODI/T20I squads (Kenya -> Afghanistan,
    Bermuda -> Nepal);
  - the ten IPL sides keep slots 45-54, exactly as in modern-2026;
  - Australia A, Masters XI, World Test XI, World One Day XI and Scottish Saltires become
    World XI 2026, OG World XI, All-Time Test / ODI / T20 XIs.
Every domestic/associate squad not listed is verified byte-for-byte unchanged.

Player abilities are not decoded. A new player copies a *donor*: an original record with the same
role, batting hand and bowling type, picked from a pool for their region, and from the elite tier
when the plan marks them as a star. Legends in the dream XIs are the original records themselves,
renamed where the 2006 game shipped an unlicensed spelling.
"""
import base64,copy,hashlib,io,json,struct,unicodedata,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
import cairosvg
from big_archive import entries,read,decompress
from fsh import replace_kit_image,replace_logo_images

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'mods/world-2026';MODERN=ROOT/'mods/modern-2026';IPL_SRC=MODERN/'sources'
ARCHIVE=ROOT/'game/Data/data.gob';ES={e[0]:e for e in entries(ARCHIVE)}
with ARCHIVE.open('rb') as stream:INDEX=stream.read(157696)
CDF='113964e05e69ab31d264fb8f15c58e5c.cdf'
RESOURCES=[]

def resource(name,data):
    assert name in ES,name
    e=ES[name];position=INDEX.index(name.encode()+b'\0')-8
    assert struct.unpack_from('>II',INDEX,position)==e[1:]
    RESOURCES.append(dict(resource=name,indexPosition=position,originalEntry=list(e[1:]),data=data))

def load(name):return decompress(read(ARCHIVE,ES[name]))
def hashed(path,ext):return hashlib.md5(path.encode()).hexdigest()+ext

ALIASES={'Mahendra Singh Dhoni':'MS Dhoni','Mitch Marsh':'Mitchell Marsh','Mitch Santner':'Mitchell Santner','Matt Short':'Matthew Short','Mitch Owen':'Mitchell Owen','Thangarasu Natarajan':'T Natarajan','Matt Renshaw':'Matthew Renshaw','Varun Chakravarthy':'Varun Chakaravarthy','Allah Ghazanfar':'AM Ghazanfar'}
def norm(name):
    name=ALIASES.get(name,name)
    return unicodedata.normalize('NFKD',name).encode('ascii','ignore').decode()

# Displayed names are at most 15 characters. Where an initial-dot-surname would read badly or
# collide, spell it out.
DISPLAY={'Mujeeb Ur Rahman':'Mujeeb','Naveen-ul-Haq':'Naveen-ul-Haq','Timm van der Gugten':'T.vanderGugten','Shadley van Schalkwyk':'S.vanSchalkwyk','Roelof van der Merwe':'R.vanderMerwe','Logan van Beek':'L.van Beek','Paul van Meekeren':'P.vanMeekeren','Jan Nicol Loftie-Eaton':'JN.Loftie-Eaton','Quinton de Kock':'Q.de Kock','Tony de Zorzi':'T.de Zorzi','Bas de Leede':'B.de Leede','Max O\'Dowd':'M.O\'Dowd','Kusal Mendis':'Kusal Mendis','Kamindu Mendis':'K.Mendis','Kusal Perera':'Kusal Perera','Mark Adair':'M.Adair','Ross Adair':'R.Adair','Harry Tector':'H.Tector','Tim Tector':'T.Tector','Barry McCarthy':'B.McCarthy','Liam McCarthy':'L.McCarthy','Shai Hope':'S.Hope','Alzarri Joseph':'A.Joseph','Shamar Joseph':'Sh.Joseph','Brendan Taylor':'B.Taylor','Sikandar Raza':'Sikandar Raza','Ben Curran':'B.Curran','Sam Curran':'S.Curran','Aasif Sheikh':'Aasif Sheikh','Aarif Sheikh':'Aarif Sheikh','Harmeet Singh':'Harmeet Singh','Jessy Singh':'Jessy Singh','Jaskaran Singh':'Jaskaran Singh','Ravinderpal Singh':'R.Singh','Tanzid Hasan':'Tanzid Hasan','Tanzim Hasan Sakib':'Tanzim Sakib','Mehidy Hasan Miraz':'Mehidy Hasan','Najmul Hossain Shanto':'N.H.Shanto','Parvez Hossain Emon':'Parvez Emon','Ibrahim Zadran':'Ibrahim Zadran','Rahmanullah Gurbaz':'R.Gurbaz','Azmatullah Omarzai':'A.Omarzai','Hashmatullah Shahidi':'H.Shahidi','Farid Ahmad Malik':'Farid Ahmad','Dipendra Singh Airee':'D.S.Airee','Gerhard Erasmus':'G.Erasmus','Mohammad Rizwan':'M.Rizwan','Mohammad Nawaz':'M.Nawaz','Mohammad Nabi':'M.Nabi','Mohammad Saifuddin':'M.Saifuddin','Mohammad Mohsin':'M.Mohsin','Sahibzada Farhan':'S.Farhan','Abdullah Shafique':'A.Shafique','Salman Ali Agha':'Salman Agha','Mustafizur Rahman':'Mustafizur','Shoriful Islam':'Shoriful Islam','Steve Smith':'S.Smith','Joe Root':'J.Root','Sadeera Samarawickrama':'Samarawickrama','Chamindu Wickramasinghe':'Wickramasinghe','Vaibhav Sooryavanshi':'V.Sooryavanshi'}
# Players from these boards are shown by full name, as the original game does for them.
FULL_NAME_BOARDS={'PAK','AFG','BAN'}

def short_name(name,abbr=None):
    if name in DISPLAY:return DISPLAY[name]
    if abbr in FULL_NAME_BOARDS and len(name)<16:return name
    if name.startswith('MS '):return 'MS.'+name[3:]
    if name.startswith('KL '):return 'KL.'+name[3:]
    if name.startswith('AM '):return 'AM.'+name[3:]
    if name.startswith('JJ '):return 'JJ.'+name[3:]
    words=name.split()
    if len(words)==1:return name
    short=''.join(w[0] for w in words[:-1])+'.'+words[-1]
    assert len(short)<16,(name,short)
    return short

# ---- donor pools: original records by region, role and tier --------------------------------
POOLS={
 'sub':dict(batR_star=['S.Tendehar','Mohammed Yosef'],batR=['R.Dravia','V.Seway','Yonas Khan','M.Jayawanderer'],batL_star=['S.Gungly'],batL=['Yevray Singh','S.Joyusupra','Salmen Buetts'],
            wkR_star=['D.Dhenier'],wkR=['Kemran Akmel'],wkL=['K.Sangaporra'],pf_star=['Shadid Akhti'],pf=['A.Agercker','Umhar Gel','Mashef Mortaz'],pl_star=['Z.Kalm'],pl=['I.Parthen','C.Vest'],
            off_star=['M.Murgalidaron'],off=['Hurvaj Singh','Shahid Melik'],leg_star=['J.Krumble'],leg=['Danis Kenaria','Shara Aphred'],sla=['M.Rafike'],arpf=['Abdel Razzeq']),
 'white':dict(batR_star=['R.Ponting','A.de Villiers'],batR=['M.Clarke','K.Pietersen','D.Martyn','M.Vaughan','R.Taylor'],batL_star=['M.Hayden'],batL=['M.Hussey','A.Strauss','A.Cook','J.Langer','S.Fleming','G.Smith'],
            wkR_star=['M.Boucher'],wkR=['B.McCullum','G.Jones'],wkL_star=['A.Gilchrist'],wkL=['A.Gilchrist'],pf_star=['G.McGrath','B.Lee','D.Steyn'],pf=['S.Harmison','S.Bond','M.Hoggard','S.Clark'],pl_star=['M.Johnson','N.Bracken'],pl=['R.Sidebottom','N.Bracken'],
            off=['G.Swann','N.Hauritz'],leg_star=['S.Warne'],leg=['S.MacGill'],slaL_star=['D.Vettori'],slaL=['M.Panesar'],sla=['A.Giles'],arpf_star=['A.Flintoff','J.Kallis'],arpf=['S.Watson','J.Oram','A.Symonds']),
 # Second-tier sides (Zimbabwe and the associates) draw from county and state players of 2006, so
 # their team ratings sit below the Test nations' instead of borrowing Lara or McGrath.
 'club':dict(batR=['M.Ramprakash','D.Hussey','M.Love','B.Hodge','D.Fulton'],batL=['M.Di Venuto','C.Rogers','J.Maher','M.Lumb','M.Carberry'],wkR=['P.Mustard','N.Pothas','C.Read'],wkL=['T.Ambrose','P.Nixon'],
            pf=['A.Bichel','D.Gough','M.Kasprowicz','T.Bresnan','S.Tait','O.Gibson'],pl=['N.Bracken','R.Sidebottom'],off=['R.Croft','S.Udal','J.Tredwell'],leg=['I.Salisbury','S.MacGill'],sla=['G.Keedy','R.Dawson'],slaL=['G.Keedy'],arpf=['D.Mascarenhas','J.Hopes','A.Noffke']),
 'afro':dict(batR_star=['H.Gibbs'],batR=['R.Sarweth','M.Sampson'],batL_star=['B.Lawrence'],batL=['C.Gaist','S.Chowdapull','A.Prince'],pf_star=['M.Ntini'],pf=['F.Edmonds','C.Colbert','H.Struck'],arpf_star=['D.Brasco'],arpf=['D.Brasco'],off=['M.Sampson']),
}
FALLBACK={'sub':'white','afro':'white','white':'sub','club':'white'}

def pick(rows,region,keys,star,seed):
    for reg in [region,FALLBACK[region],'white']:
        pool=POOLS[reg]
        for key in keys:
            # Stars draw only from the elite tier when the region has one for this role.
            names=pool.get(key+'_star') if star and pool.get(key+'_star') else pool.get(key,[])+([] if star else pool.get(key+'_star',[]))
            if names:return rows[names[seed%len(names)]]
    raise KeyError((region,keys))

def donor(rows,player,region,seed):
    role,bat,bowl,star=player['role'],player['bat'],player['bowl'],player['star']
    if role=='wk':return pick(rows,region,['wk'+bat],star,seed)
    if role=='bowl' or (role=='ar' and bowl in ('off','leg','sla','lws')):
        key={'pf':'pf','pl':'pl','off':'off','leg':'leg','lws':'leg','sla':'slaL' if bat=='L' else 'sla','-':'pf'}[bowl]
        if role=='ar' and bowl=='pf':key='arpf'
        chain=[key]+(['sla'] if key=='slaL' else [])+(['pl'] if key=='lws' else [])
        return pick(rows,region,chain,star,seed)
    if role=='ar':return pick(rows,region,['arpf','pf'],star,seed)
    return pick(rows,region,['bat'+bat],star,seed)

def parse(spec,look):
    """'Name|role,bat,bowl[,*][,region]' -> dict; bare 'Name' -> None (attrs come from elsewhere)."""
    if '|' not in spec:return norm(spec),None
    name,attrs=spec.split('|');parts=attrs.split(',')
    region=next((p for p in parts[3:] if p in POOLS),look)
    return norm(name),dict(role=parts[0],bat=parts[1],bowl=parts[2],star='*' in parts[3:],region=region)

# IPL-only players: derive attributes the way modern-2026 did.
LEFT={'Axar Patel','Ishan Kishan','Shivam Dube','Yashasvi Jaiswal','Vaibhav Sooryavanshi','Sai Sudharsan','Abhishek Sharma','Ravindra Jadeja','Krunal Pandya','Devdutt Padikkal','Venkatesh Iyer','Rinku Singh','Nitish Rana','David Miller','Tilak Varma','Sherfane Rutherford','Nicholas Pooran','Rishabh Pant','Travis Head','Shimron Hetmyer','Sam Curran','Marco Jansen','Akeal Hosein','Mitchell Santner','Rachin Ravindra','Quinton de Kock','Ryan Rickelton','Abishek Porel','Washington Sundar','Nehal Wadhera','Cooper Connolly','Kamindu Mendis','Shahbaz Ahmed','Ben Duckett','Jacob Bethell','Sunil Narine','Kagiso Rabada','Prabhsimran Singh','Priyansh Arya','Riyan Parag','Musheer Khan'}
LEFT_PACE={'Arshdeep Singh','Trent Boult','Mitchell Starc','Khaleel Ahmed','Mohsin Khan','Jaydev Unadkat','Yash Dayal','T Natarajan','Nandre Burger','Luke Wood','Marco Jansen','Sam Curran','Arjun Tendulkar','Mukesh Choudhary','Mustafizur Rahman','Dilshan Madushanka','Kwena Maphaka','Spencer Johnson','Ben Dwarshuis'}
SPIN={'Kuldeep Yadav','Rashid Khan','Ravi Bishnoi','Yuzvendra Chahal','Varun Chakaravarthy','Suyash Sharma','Noor Ahmad','Rahul Chahar','Shreyas Gopal','Mayank Markande','Digvesh Singh Rathi','Harsh Dubey','Zeeshan Ansari','Vignesh Puthur','Wanindu Hasaranga','Adil Rashid','Rehan Ahmed'}
OFF={'Sunil Narine','Washington Sundar','Will Jacks','Naman Dhir','Aiden Markram','Glenn Phillips','Liam Livingstone','AM Ghazanfar','Jayant Yadav','Riyan Parag'}
LA_SPIN={'Axar Patel','Ravindra Jadeja','Krunal Pandya','Mitchell Santner','Akeal Hosein','Shahbaz Ahmed','Sai Kishore','Manav Suthar','Manimaran Siddharth','Swapnil Singh','Keshav Maharaj','George Linde','Harpreet Brar'}
STARS={'Rishabh Pant','Yashasvi Jaiswal','Suryakumar Yadav','Sunil Narine','Trent Boult','Heinrich Klaasen','Nicholas Pooran','Mohammed Shami','Yuzvendra Chahal','Rajat Patidar','Sai Sudharsan','Liam Livingstone'}
OVERSEAS_LOOK={'afro':{'Kagiso Rabada','Lungi Ngidi','Romario Shepherd','Rovman Powell','Shimron Hetmyer','Sherfane Rutherford','Nicholas Pooran','Jason Holder','Akeal Hosein','Sunil Narine','Blessing Muzarabani','Kwena Maphaka','Temba Bavuma','Andre Russell','Kieron Pollard'},
               'white':{'Phil Salt','Jos Buttler','Travis Head','Pat Cummins','Mitchell Starc','Josh Hazlewood','Cameron Green','Glenn Phillips','Trent Boult','Liam Livingstone','Tim David','Mitchell Marsh','Aiden Markram','David Miller','Heinrich Klaasen','Quinton de Kock','Ryan Rickelton','Marco Jansen','Anrich Nortje','Tristan Stubbs','Dewald Brevis','Corbin Bosch','Gerald Coetzee','Nandre Burger','Josh Inglis','Jake Fraser-McGurk','Marcus Stoinis','Mitchell Santner','Rachin Ravindra','Finn Allen','Tim Seifert','Lockie Ferguson','Kyle Jamieson','Matt Henry','Jacob Duffy','Adam Milne','Will Jacks','Sam Curran','Jofra Archer','Jamie Overton','Jacob Bethell','Ben Duckett','Tom Banton','Jordan Cox','Brydon Carse','Luke Wood','Matthew Short','Matthew Breetzke','Donovan Ferreira','Ben Dwarshuis','Nathan Ellis','Xavier Bartlett','Spencer Johnson','Cooper Connolly','Mitchell Owen','Jack Edwards','Richard Gleeson','Zak Foulkes','Dian Forrester','Connor Esterhuizen','Lhuan-dre Pretorius','David Payne','Kyle Jamieson','George Linde','Steve Smith','David Warner','Matthew Renshaw','Adam Zampa','Glenn Maxwell'}}

def ipl_attrs(p):
    name=norm(p['name'])
    bat='L' if name in LEFT else 'R'
    if p.get('isWicketKeeper') or name in {'Phil Salt','Heinrich Klaasen','MS Dhoni','KL Rahul','Sanju Samson','Jitesh Sharma','Dhruv Jurel'}:role,bowl='wk','-'
    else:
        role={'bowler':'bowl','allrounder':'ar'}.get(p.get('role'),'bat')
        bowl='sla' if name in LA_SPIN else 'off' if name in OFF else 'leg' if name in SPIN else 'pl' if name in LEFT_PACE else 'pf' if role!='bat' else '-'
    region=next((r for r,s in OVERSEAS_LOOK.items() if name in s),'sub')
    return dict(role=role,bat=bat,bowl=bowl,star=name in STARS,region=region)

JERSEY={'Virat Kohli':18,'Rohit Sharma':45,'Jasprit Bumrah':93,'Shubman Gill':77,'Hardik Pandya':33,'Ravindra Jadeja':8,'KL Rahul':1,'Pat Cummins':30,'Mitchell Starc':56,'Travis Head':62,'Steve Smith':49,'Joe Root':66,'Harry Brook':88,'Jos Buttler':63,'Babar Azam':56,'Shaheen Afridi':10,'Rashid Khan':19,'Kagiso Rabada':25,'Quinton de Kock':12,'Kane Williamson':22,'Glenn Maxwell':32,'Suryakumar Yadav':63,'David Warner':31,'Andre Russell':12,'Kieron Pollard':55,'Sunil Narine':74}

# ---- kits and badges ----------------------------------------------------------------------
def svg_image(svg,size):
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(),output_width=size[0],output_height=size[1]))).convert('RGBA')

def badge_svg(team):
    """An original roundel in the team's colours, never a board's trademarked crest."""
    c,a=team['colour'],team['accent'];ink=team.get('textColour','#ffffff')
    label=team['abbr'];fs=46 if len(label)<=2 else 38 if len(label)==3 else 30
    star='<path d="M64 14l5 11 12 1-9 8 3 12-11-6-11 6 3-12-9-8 12-1z" fill="{a}"/>'.format(a=a)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128">'
            f'<circle cx="64" cy="64" r="60" fill="{c}" stroke="{a}" stroke-width="7"/>'
            f'<circle cx="64" cy="64" r="44" fill="none" stroke="{a}" stroke-opacity=".55" stroke-width="2"/>{star}'
            f'<text x="64" y="{78 if fs>40 else 76}" text-anchor="middle" font-family="Arial Black,Arial,sans-serif" font-weight="900" font-size="{fs}" fill="{ink}">{label}</text>'
            f'<path d="M30 96q34 18 68 0" fill="none" stroke="{a}" stroke-width="5" stroke-linecap="round"/></svg>')

def crest(team):
    file=IPL_SRC/(team['slug']+'-crest.svg') if team.get('slug') else None
    if file and file.exists():return svg_image(file.read_text(),(128,128))
    svg=badge_svg(team)
    folder=OUT/'badges';folder.mkdir(parents=True,exist_ok=True);(folder/(team['code']+'.svg')).write_text(svg)
    return svg_image(svg,(128,128))

def vector_texture(team,kind,folder_name):
    colour=team['colour'];accent=team['accent'];chest=team.get('chest') or team.get('sponsor','');ink=team.get('textColour','white')
    badge=crest(team);buf=io.BytesIO();badge.save(buf,format='PNG');image='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()
    slug=team.get('slug','')
    if kind=='kit1':
        w=h=512;parts=[f'<rect width="512" height="512" fill="{colour}"/>']
        if slug=='lucknow-super-giants':parts+=[f'<path d="M{x} 0l45 220h-24L{x-24} 0z" fill="{accent}"/>' for x in range(25,520,64)]
        elif slug=='punjab-kings':parts+=[f'<path d="M0 0h82l18 220H0zM430 0h82v220h-100z" fill="{accent}"/>']
        elif slug=='royal-challengers-bengaluru':parts+=[f'<path d="M0 155h512v357H0z" fill="{accent}"/>']
        elif slug=='rajasthan-royals':parts+=[f'<path d="M0 125l512 25v362H0z" fill="{accent}"/>']
        elif not slug:
            # National/dream-XI shirts: a shoulder sweep and side panels in the accent colour.
            parts+=[f'<path d="M0 0h512v34q-256 40-512 0z" fill="{accent}"/>',f'<path d="M0 196h512v14H0zM0 222h22v290H0zM348 222h22v290h-22z" fill="{accent}"/>',
                    f'<path d="M0 60q256 60 512 0v10q-256 60-512 0z" fill="{accent}" opacity=".55"/>']
        else:parts+=[f'<path d="M0 5h512v12H0zM0 196h512v14H0zM0 222h14v290H0zM356 222h13v290h-13z" fill="{accent}"/>']
        size=17 if len(chest)>10 else 24
        parts+=['<rect width="512" height="512" fill="url(#cloth)" opacity=".22"/>',
                '<path d="M0 220H512M380 220V512" stroke="#001329" stroke-opacity=".4" stroke-width="3"/>',
                f'<path d="M240 75q-28 32 0 66l15-13q-18-22 0-42z" fill="{accent}"/>',
                f'<g transform="translate(365 110) rotate(-90)"><image href="{image}" x="-84" y="-60" width="40" height="40"/><text x="5" y="7" font-family="Arial,sans-serif" font-weight="bold" font-size="{size}" text-anchor="middle" fill="{ink}">{chest}</text><text x="3" y="31" text-anchor="middle" fill="{ink}" font-family="Arial" font-size="12">{team["abbr"]}</text></g>',
                '<rect x="382" y="356" width="130" height="156" fill="#d5d9df"/><path d="M386 424h110v40H386z" fill="#20242a"/><path d="M400 369l50 55m-40-57 50 55m-38-56 49 55" stroke="white" stroke-width="6"/>']
    else:
        w=h=256 if kind!='helm' else 128
        helm=team.get('helmet',colour if kind=='helm' else colour)
        parts=[f'<rect width="{w}" height="{h}" fill="{helm}"/>',f'<rect width="{w}" height="{h}" fill="url(#cloth)" opacity=".2"/>']
        if kind in ['kit2','kit3']:
            parts+=[f'<path d="M82 0h12v256H82zM232 0h12v256h-12z" fill="{accent}"/>']
            parts+=[f'<path d="M95 {y}H230" stroke="white" stroke-opacity=".24" stroke-width="3"/>' for y in range(30,250,15)]
            parts+=['<rect width="74" height="256" fill="#e1e3e6"/><path d="M0 100h74v8H0zM0 170h74v8H0z" fill="#333"/>']
        elif kind=='accs':parts+=[f'<image href="{image}" x="170" y="8" width="42" height="42"/><image href="{image}" x="165" y="153" width="38" height="38"/>',f'<path d="M0 80h256v8H0z" fill="{accent}"/>']
        else:parts+=[f'<image href="{image}" x="48" y="38" width="38" height="38"/>']
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}"><defs><linearGradient id="cloth" x2="0.8" y2="1"><stop stop-color="white"/><stop offset=".25" stop-color="#131b2b"/><stop offset=".38" stop-color="white"/><stop offset=".65" stop-color="#091326"/><stop offset="1" stop-color="white"/></linearGradient></defs>'+''.join(parts)+'</svg>'
    folder=OUT/'kits'/folder_name;folder.mkdir(parents=True,exist_ok=True);(folder/(kind+'.svg')).write_text(svg)
    im=svg_image(svg,(w,h));im.save(folder/(kind+'.png'));return im

# Logo textures per slot. Two-letter logo codes are shared by some pairs of teams (Australia /
# Australia A, Ireland / Ireland County ...); these were told apart by rendering the textures.
LOGOS={0:['4277d1a7688da310197f0e3fc28d4ee6.fsh','af9c2c55d4de2d873214719ecdde5377.fsh'],1:['313f51d7b667e5ce36961d0e07427c20.fsh','5854120b800c3df9f65dc5c2b7b130f4.fsh'],
       3:['ed39e69b1355423abaedd10fcb1719cb.fsh','ac5c30e62b64bb0aabd224bb12d56811.fsh'],7:['4fae282f9a5075483f127d9f96823eb5.fsh','39ba9905b8a12a053c75f0a36e0f5214.fsh'],
       13:['a6ffda9db1648ec72a46cf6d9a8c7ecf.fsh','16879cb868a61f1ebf4da6dc0fe6a736.fsh'],15:['67692c1e4b0f8fcebac73e05a4e3dbcb.fsh','63b47de421b5bd5fdd1eed338072711d.fsh'],
       19:['704da3bdb30aa7be9784aadeb25f7b80.fsh','285206e2458d2aa84862fca0121e4f28.fsh'],20:['96ce9891100700ada1854129d13cec6a.fsh','7804d0aa774c46a305bb52054feb46bc.fsh'],
       21:['beaaaa0cbfce4460f273c925c8abbdf1.fsh','96d4c18d1c331ecb1feeffdb0bc2b1e0.fsh'],23:['42bc2460a47c5b3d5a0cf5d692fa9eb6.fsh','11ee5af2ea07d2bf3e27812b1937f58c.fsh'],
       27:['25c601f7774e5b742fdee088e856309e.fsh','efa82cbb524e7b445a91bf31d48272af.fsh'],30:['4d7d720c6a3a1e1a3a2af058fa2d7d00.fsh','a81c5889aa1f9ba6868edf8074118bb5.fsh'],
       32:['a44e6460911658681c039e112db17486.fsh','612d1779391a21ca2dcfd3c8d3d7e617.fsh'],39:['362d4424488f356f7a1b16fd13e2c334.fsh','2fa4429e69de01ce670e4c738c9b9104.fsh'],
       43:['025245205656dff9f8af52c6ac4e3d78.fsh','21fd7bbe631165a8c56ad3c5563962f6.fsh'],44:['97a96c0b7d61af237764622f9270a98f.fsh','347986af1f0d2d3c159198bce503c044.fsh'],
       55:['6e3e30a0ec875fed23bc18a05b210cfb.fsh','7edf5d560a1d9b47dce98c638f1e45c8.fsh'],56:['277ff087cf0fe54c9948a4b5623c8953.fsh','06597e8ecf69c3f1634755581dfd440b.fsh'],
       57:['3522bfe8729c768aea0c021a42b149c4.fsh','18f669170a67d57c0f50fec631ddfed0.fsh'],58:['1c715b30615b4ae5d5571499bc00e083.fsh','4d1472da009198e0a30eff7b2e57a378.fsh'],
       59:['200d5e6cd51b8bd0a98481439a861251.fsh','cec942de953349d59d6eb353b4e046a9.fsh'],
       # Ireland and Ireland County ship the identical crest four times; all four take Ireland's.
       60:['b4d0a548e49e3472d8e71e016bfbdd15.fsh','34041cab855c97a5471f8307c7c7ef7d.fsh','cc34c9346b72db048c0db9d1cffa03a3.fsh','1290856e29f85fa196950a9724abf52a.fsh'],
       61:['f5be5e9b75affac8aabb4fd5e593817e.fsh','90a7167331a1b253e90ca2e10a0a21da.fsh']}

def build():
    original=load(CDF);data=bytearray(original)
    plan=json.loads((OUT/'team-plan.json').read_text())['teams']
    modern=json.loads((MODERN/'team-plan.json').read_text())
    ipl=[t for t in modern if t['slug']!='india-odi-2026']
    logo_map=json.loads((MODERN/'logo-map.json').read_text())
    for t in ipl:LOGOS[t['slot']]=logo_map[str(t['slot'])]

    rows={};pid_of_row={}
    for r in range(1200):
        s=r*360+4;nm=original[s+4:s+20].split(b'\0')[0].decode('latin1');pid_of_row[r]=struct.unpack_from('<H',original,s)[0]
        rows.setdefault(nm,r)
    replaced={t['slot'] for t in plan}|{t['slot'] for t in ipl}
    team_slots=list(range(63))
    preserved=[s for s in team_slots if s not in replaced]
    protected=set()
    for slot in preserved:protected.update(struct.unpack_from('<20H',original,432004+2808*slot))
    protected.discard(65535)
    legend_rows={}
    for team in plan:
        for spec in team['players']+[team['captain']]:
            if spec.startswith('og:'):
                og,_,display=spec[3:].partition('=');assert og in rows,og;legend_rows[rows[og]]=display or og
    protected_rows={r for r in range(1200) if pid_of_row[r] in protected}|set(legend_rows)
    free=[r for r in range(1,1199) if r not in protected_rows]
    free.sort(key=lambda r:(bool(original[r*360+8:r*360+24].split(b'\0')[0]),-r))
    original_ids=set(pid_of_row.values())
    new_ids=iter(i for i in range(30000,32768) if i not in original_ids)

    # Attribute table: national plan specs win, then IPL-derived.
    attrs={}
    for team in plan:
        for spec in team['players']:
            if spec.startswith('og:'):continue
            name,a=parse(spec,team.get('look','white'))
            if a:
                if team.get('tier')=='club':a=dict(a,region='club' if not a['star'] else a['region'],star=False)
                attrs[name]=a
    ipl_players={}
    for t in ipl:
        src=json.loads((IPL_SRC/(t['slug']+'.json')).read_text());pool={p['name']:p for p in src['squad']['players']}
        ipl_players[t['slug']]=(src,[pool[n] for n in t['players'].split('|')])
        for p in ipl_players[t['slug']][1]:attrs.setdefault(norm(p['name']),ipl_attrs(p))

    allocated={};player_details=[];team_details=[];seed=[0]
    abbr_of={}
    for team in plan:
        for spec in team['players']:
            if not spec.startswith('og:'):abbr_of.setdefault(parse(spec,'white')[0],team['abbr'])

    def new_player(name):
        if name in allocated:return allocated[name][0]
        a=attrs.get(name);assert a,f'No attributes for {name}'
        row=free.pop(0);template=donor(rows,a,a['region'],seed[0]);seed[0]+=1;pid=next(new_ids)
        start=row*360+4;src=template*360+4
        data[start:start+360]=original[src:src+360]
        struct.pack_into('<HH',data,start,pid,65535)
        label=short_name(name,abbr_of.get(name)).encode('latin1');assert len(label)<16,label
        data[start+4:start+20]=label.ljust(16,b'\0')
        data[start+20:start+100]=bytes(80)   # career counters reset; packed abilities kept
        allocated[name]=(pid,row)
        player_details.append(dict(name=name,displayName=label.decode('latin1'),id=pid,row=row,templateRow=template,templateName=original[template*360+8:template*360+24].split(b'\0')[0].decode('latin1'),**a))
        return pid

    for row,display in legend_rows.items():
        start=row*360+4;data[start+4:start+20]=display.encode('latin1')[:15].ljust(16,b'\0')

    def legend_id(spec):
        og=spec[3:].partition('=')[0];return pid_of_row[rows[og]]

    info=ET.fromstring(load('be2970b0ada8e42cf891ce60ffe69575.xml'))
    manager=ET.fromstring(load('730eef3fd7726e43de955f21083ab000.xml'))
    legacy=ET.fromstring(load('49ad277eb4663535abe0d4b1ec726023.xml'))

    def write_team(slot,code,title,short,abbr,ids,numbers,captain_id,standard,text_colour,source,names,replaces_note=None):
        off=432004+slot*2808;template_off=432004+13*2808
        data[off-24:off-24+2808]=original[template_off-24:template_off-24+2808]
        data[off-24:off-4]=bytes(numbers+[0]*(20-len(numbers)))
        struct.pack_into('<20H',data,off,*(ids+[65535]*(20-len(ids))))
        struct.pack_into('<I',data,off+40,slot)
        struct.pack_into('<H',data,off+46,captain_id)
        node=next(t for t in info.findall('team') if int(t.get('Index'))==slot)
        old=node.get('TeamName')
        node.set('TeamName',title);node.set('TeamNameShort',short);node.set('Abbreviation',abbr)
        if standard is not None:node.set('StandardOfCricket',str(standard))
        mgr=next(t for t in manager.findall('./teams/team') if int(t.get('id'))==slot);mgr.set('name',title)
        for kit in mgr.findall('kit'):kit.set('namecolour',text_colour.upper());kit.set('numbercolour',text_colour.upper())
        for t in legacy.iter('team'):
            if t.get('Abbreviation','').lower()==code:t.set('TeamName',title);t.set('TeamNameShort',short)
        team_details.append(dict(name=title,slot=slot,code=code,replaces=old,captain=names[ids.index(captain_id)] if captain_id in ids else None,source=source,selectedPlayers=names,**({'note':replaces_note} if replaces_note else {})))

    for team in plan:
        ids=[];names=[];numbers=[]
        for spec in team['players']:
            if spec.startswith('og:'):
                pid=legend_id(spec);og,_,display=spec[3:].partition('=');names.append(display or og);ids.append(pid);numbers.append(0)
            else:
                name=parse(spec,'white')[0];ids.append(new_player(name));names.append(name);numbers.append(JERSEY.get(name,0)%100)
        assert len(ids)<=20 and len(set(ids))==len(ids),team['name']
        cap=team['captain'];captain_id=legend_id(cap) if cap.startswith('og:') else allocated[norm(cap)][0]
        write_team(team['slot'],team['code'],team['name'],team['short'],team['abbr'],ids,numbers,captain_id,team.get('standard'),team.get('textColour','#ffffff'),team['source'],names,team.get('replacesNote'))
    for t in ipl:
        src,chosen=ipl_players[t['slug']]
        ids=[new_player(norm(p['name'])) for p in chosen];names=[norm(p['name']) for p in chosen]
        numbers=[int(p.get('jerseyNumber') or 0)%100 for p in chosen]
        captain=norm(next(p['name'] for p in src['squad']['players'] if p.get('isCaptain')))
        write_team(t['slot'],t['code'],'Royal Challengers' if t['abbr']=='RCB' else src['title'],t['short'],t['abbr'],ids,numbers,allocated[captain][0],3,'#ffffff',src['sourceUrl'],names)

    assert len(data)==len(original)
    for row in protected_rows-set(legend_rows):
        s=row*360+4;assert data[s:s+360]==original[s:s+360],f'OG player overwritten: {row}'
    for row in legend_rows:
        s=row*360+4;assert data[s+20:s+360]==original[s+20:s+360] and data[s:s+4]==original[s:s+4],f'Legend record altered beyond its name: {row}'
    for slot in preserved:
        s=432004+2808*slot-24;assert data[s:s+2808]==original[s:s+2808],f'OG squad overwritten: {slot}'

    resource(CDF,bytes(data))
    for filename,xml in [('be2970b0ada8e42cf891ce60ffe69575.xml',info),('730eef3fd7726e43de955f21083ab000.xml',manager),('49ad277eb4663535abe0d4b1ec726023.xml',legacy)]:
        resource(filename,ET.tostring(xml,encoding='utf-8',xml_declaration=True))
    kit_teams=[(t,t['code']) for t in plan]+[(dict(t,chest=t['sponsor']),t['slug']) for t in ipl]
    for team,folder in kit_teams:
        for kind,suffix in [('kit1','colouredkit1'),('kit2','colouredkit2'),('kit3','colouredkit3'),('accs','colouredaccessories'),('helm','helm')]:
            filename=hashed('teams/'+team['code']+'/'+suffix,'.fsh')
            resource(filename,replace_kit_image(load(filename),vector_texture(team,kind,folder)))
        for filename in LOGOS[team['slot']]:resource(filename,replace_logo_images(load(filename),crest(team)))

    previous=[]
    if (OUT/'manifest.json').exists():
        old=json.loads((OUT/'manifest.json').read_text())
        previous=(old.get('previousLayouts',[])+[dict(size=old['size'],resources=[dict(resource=r['resource'],offset=r['offset'],size=r['size']) for r in old['resources']])])[-3:]
    payload=bytearray();manifest=[]
    for r in RESOURCES:
        content=r.pop('data');r.update(offset=len(payload),size=len(content),sha256=hashlib.sha256(content).hexdigest());payload+=content;manifest.append(r)
    (OUT/'world-pack.bin').write_bytes(payload)
    # Static hosts cap a file at 25 MiB (Cloudflare Pages), so the pack is also published as
    # verified 20 MiB parts. Loaders fetch the parts in order and check each before joining them;
    # the joined bytes must still match the pack's own sha256.
    for old in OUT.glob('world-pack.part*.bin'):old.unlink()
    parts=[]
    for index,start in enumerate(range(0,len(payload),20*1024*1024)):
        piece=payload[start:start+20*1024*1024];name=f'world-pack.part{index}.bin'
        (OUT/name).write_bytes(piece);parts.append(dict(file=name,size=len(piece),sha256=hashlib.sha256(piece).hexdigest()))
    if previous and previous[-1]['size']==len(payload) and [r['size'] for r in previous[-1]['resources']]==[r['size'] for r in manifest]:previous=previous[:-1]
    (OUT/'manifest.json').write_text(json.dumps(dict(id='world-2026-v1',file='world-pack.bin',parts=parts,originalSize=ARCHIVE.stat().st_size,size=len(payload),sha256=hashlib.sha256(payload).hexdigest(),
        resources=manifest,previousLayouts=previous,teams=team_details,players=player_details,legends=sorted(legend_rows.values()),preservedTeamSlots=preserved,protectedPlayerRows=sorted(protected_rows),
        kitNote='Fan-made kits in each side\'s 2026 colours with original roundel badges; not official crests or downloadable game skins.',
        ratingNote='New players copy an original record of the same role, hand and bowling type (elite donors for stars); career stats reset; not official ratings.'),indent=1)+'\n')
    print(f'Built {len(plan)+len(ipl)} teams, {len(allocated)} new players, {len(legend_rows)} legends, {len(RESOURCES)} resources, {len(payload)/1e6:.1f} MB. '
          f'{len(protected_rows)-len(legend_rows)} OG player records and {len(preserved)} OG squads verified unchanged.')

if __name__=='__main__':build()
