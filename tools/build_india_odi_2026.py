"""Build a reversible India roster trial from the local game's own database.
Only names, India squad membership and captain are edited. Legacy abilities,
faces, statistics and handedness remain as donor placeholders, not 2026 ratings.
"""
import hashlib
import json
import struct
from pathlib import Path
from big_archive import entries, read, decompress

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'game/Data/data.gob'
OUT = ROOT / 'mods/india-odi-2026'
RESOURCE = '113964e05e69ab31d264fb8f15c58e5c.cdf'
SOURCE = 'https://www.bcci.tv/news/article/indias-odi-and-test-squads-for-new-zealand-tour-announced'
# Display name, source record, source-era player, squad role.
PLAYERS = [
    ('S.Gill', 525, 'Rahul Dravid', 'Captain'),
    ('R.Sharma', 530, 'Virender Sehwag', 'Batter'),
    ('V.Kohli', 527, 'Sachin Tendulkar', 'Batter'),
    ('S.Iyer', 544, 'Mohammad Kaif', 'Vice-captain'),
    ('KL.Rahul', 545, 'MS Dhoni', 'Wicketkeeper'),
    ('N.K.Reddy', 547, 'Reetinder Sodhi', 'All-rounder'),
    ('A.Patel', 554, 'Yuvraj Singh', 'All-rounder'),
    ('A.Kamboj', 541, 'Lakshmipathy Balaji', 'Bowler'),
    ('K.Yadav', 524, 'Anil Kumble', 'Bowler'),
    ('M.Siraj', 536, 'Ajit Agarkar', 'Bowler'),
    ('A.Singh', 558, 'Zaheer Khan', 'Bowler'),
    ('G.Brar', 553, 'Shantakumaran Sreesanth', 'Bowler'),
    ('R.Gaikwad', 548, 'Aakash Chopra', 'Batter'),
    ('N.Dhir', 529, 'Ashish Nehra placeholder', 'All-rounder'),
    ('I.Kishan', 552, 'Parthiv Patel', 'Wicketkeeper'),
    ('P.Krishna', 538, 'RP Singh', 'Bowler; subject to fitness'),
]

def build():
    OUT.mkdir(parents=True, exist_ok=True)
    entry = next(e for e in entries(ARCHIVE) if e[0] == RESOURCE)
    original = decompress(read(ARCHIVE, entry))
    assert len(original) == 620140 and original[:4] == bytes.fromhex('000c0000')
    data = bytearray(original)
    players = []
    ids = []
    for name, row, donor, role in PLAYERS:
        offset = row * 360 + 8
        old_name = original[offset:offset+16].split(b'\0')[0].decode('ascii')
        assert old_name and len(name.encode('ascii')) < 16
        data[offset:offset+16] = name.encode('ascii').ljust(16, b'\0')
        player_id = struct.unpack_from('<H', original, row * 360 + 4)[0]
        ids.append(player_id)
        players.append(dict(name=name, role=role, playerId=player_id, row=row,
                            originalName=old_name, donor=old_name))
    squad_offset = 468508
    assert struct.unpack_from('<I', original, squad_offset+40)[0] == 13
    struct.pack_into('<20H', data, squad_offset, *(ids + [65535]*4))
    struct.pack_into('<H', data, squad_offset+46, ids[0])
    # A BIG resource is either RefPack encoded or raw. Appending raw data leaves
    # every original resource intact, and the two directory fields select it.
    raw_index = ARCHIVE.read_bytes()[:157696]
    index_position = raw_index.index(RESOURCE.encode('ascii') + b'\0') - 8
    assert struct.unpack_from('>II', raw_index, index_position) == entry[1:]
    output = OUT / 'india-odi-2026.cdf'
    output.write_bytes(data)
    manifest = dict(id='india-odi-2026-v1', title='India ODI 2026 (roster trial)',
        source=SOURCE, squadDate='2026-10-16', scope='New Zealand tour, first three ODIs',
        limitations='Names, 16-player squad and captain updated. Original models, kits, abilities, handedness and career statistics remain placeholders.',
        resource=RESOURCE, archive='Data/data.gob', originalSize=ARCHIVE.stat().st_size,
        indexPosition=index_position, originalEntry=list(entry[1:]),
        file='india-odi-2026.cdf', size=len(data), sha256=hashlib.sha256(data).hexdigest(), players=players)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    assert len(data)==len(original)
    changed = {i for i,(a,b) in enumerate(zip(original,data)) if a!=b}
    allowed = set(range(squad_offset, squad_offset+40)) | set(range(squad_offset+46,squad_offset+48))
    for _, row, _, _ in PLAYERS: allowed.update(range(row*360+8,row*360+24))
    assert changed <= allowed
    assert len(set(ids)) == 16
    print(f'Built {output.name}: 16 players, {len(changed)} changed bytes, original archive untouched')

if __name__ == '__main__':
    build()
