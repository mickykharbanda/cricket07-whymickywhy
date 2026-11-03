"""Read EA BIGF archives without modifying the source archive."""
import struct
from pathlib import Path

def entries(path):
    path = Path(path)
    with path.open('rb') as stream:
        header = stream.read(16)
        if header[:4] not in (b'BIGF', b'BIG4'):
            raise ValueError('Not an EA BIG archive')
        count = struct.unpack('>I', header[8:12])[0]
        for _ in range(count):
            offset, size = struct.unpack('>II', stream.read(8))
            name = bytearray()
            while True:
                char = stream.read(1)
                if not char:
                    raise ValueError('Truncated archive index')
                if char == b'\0':
                    break
                name += char
            yield name.decode('ascii'), offset, size

def read(path, entry):
    with Path(path).open('rb') as stream:
        stream.seek(entry[1])
        data = stream.read(entry[2])
        if len(data) != entry[2]:
            raise ValueError('Truncated archive entry')
        return data

def decompress(data):
    """Decode EA RefPack streams, or return an uncompressed resource as-is."""
    if data[:2] != b'\x10\xfb':
        return data
    expected = int.from_bytes(data[2:5], 'big')
    pos = 5
    result = bytearray()
    while pos < len(data):
        control = data[pos]
        pos += 1
        if control >= 0xfc:
            literals, length, distance = control & 3, 0, 0
        elif control >= 0xe0:
            literals, length, distance = ((control & 31) << 2) + 4, 0, 0
        elif control >= 0xc0:
            a, b, c = data[pos:pos+3]
            pos += 3
            literals = control & 3
            length = ((control & 12) << 6) + c + 5
            distance = ((control & 16) << 12) + (a << 8) + b + 1
        elif control >= 0x80:
            a, b = data[pos:pos+2]
            pos += 2
            literals = a >> 6
            length = (control & 63) + 4
            distance = ((a & 63) << 8) + b + 1
        else:
            a = data[pos]
            pos += 1
            literals = control & 3
            length = ((control & 28) >> 2) + 3
            distance = ((control & 96) << 3) + a + 1
        result.extend(data[pos:pos+literals])
        pos += literals
        if length:
            if distance > len(result):
                raise ValueError('Invalid RefPack distance')
            for _ in range(length):
                result.append(result[-distance])
        if control >= 0xfc:
            break
    if len(result) != expected:
        raise ValueError(f'RefPack size mismatch: {len(result)} != {expected}')
    return bytes(result)
