"""Read EA SHPI texture resources; write native BGRA8888 textures."""
import struct
from pathlib import Path

def decode(data):
    from PIL import Image
    assert data[:4] == b'SHPI'
    name = data[16:20]
    offset = struct.unpack_from('<I', data, 20)[0]
    kind = data[offset]
    width, height = struct.unpack_from('<HH', data, offset+4)
    pixels = data[offset+16:]
    if kind == 0x7d:
        image = Image.frombytes('RGBA', (width, height), pixels[:width*height*4], 'raw', 'BGRA')
    elif kind in [0x60, 0x61, 0x62]:
        import io
        fourcc = {0x60:b'DXT1', 0x61:b'DXT3', 0x62:b'DXT5'}[kind]
        header = bytearray(128)
        header[:4] = b'DDS '
        struct.pack_into('<7I',header,4,124,0x81007,height,width,0,0,1)
        struct.pack_into('<II',header,76,32,4)
        header[84:88] = fourcc
        struct.pack_into('<I',header,108,0x1000)
        image = Image.open(io.BytesIO(header+pixels)).convert('RGBA')
    else: raise ValueError(f'Unsupported FSH pixel kind {kind:x}')
    return name, image

def encode(image, name=b'kit1'):
    image=image.convert('RGBA'); width,height=image.size
    pixels=image.tobytes('raw','BGRA'); size=32+16+len(pixels)
    header=bytearray(48)
    header[:4]=b'SHPI'
    struct.pack_into('<II',header,4,size,1)
    header[12:16]=b'G359';header[16:20]=name
    struct.pack_into('<I',header,20,32)
    header[24:32]=b'Buy ERTS'
    struct.pack_into('<IHH',header,32,((16+len(pixels))<<8)|0x7d,width,height)
    return bytes(header)+pixels

def encode_dxt5(image, name=b'kit1'):
    import io
    temp=io.BytesIO();image.convert('RGBA').save(temp,format='DDS',pixel_format='DXT5')
    pixels=temp.getvalue()[128:];width,height=image.size
    header=bytearray(48);header[:4]=b'SHPI'
    struct.pack_into('<II',header,4,48+len(pixels),1)
    header[12:16]=b'G359';header[16:20]=name
    struct.pack_into('<I',header,20,32);header[24:32]=b'Buy ERTS'
    struct.pack_into('<IHH',header,32,((16+len(pixels))<<8)|0x62,width,height)
    return bytes(header)+pixels


def replace_logo_images(original, logo):
    """Replace pixels while preserving native headers, mip tails and attachments."""
    count=struct.unpack_from('<I',original,8)[0]
    result=bytearray(original)
    for index in range(count):
        old_offset=struct.unpack_from('<I',original,20+8*index)[0]
        width,height=struct.unpack_from('<HH',original,old_offset+4)
        pixels=texture_pixels(logo.resize((width,height)),original[old_offset])
        assert old_offset+16+len(pixels)<=len(result)
        result[old_offset+16:old_offset+16+len(pixels)]=pixels
    return bytes(result)

def texture_pixels(image, kind):
    import io
    image=image.convert('RGBA')
    if kind==0x7d:return image.tobytes('raw','BGRA')
    fourcc={0x60:'DXT1',0x61:'DXT3',0x62:'DXT5'}[kind]
    temp=io.BytesIO();image.save(temp,format='DDS',pixel_format=fourcc)
    return temp.getvalue()[128:]

def replace_kit_image(original, image):
    offset=struct.unpack_from('<I',original,20)[0]
    size=struct.unpack_from('<HH',original,offset+4)
    pixels=texture_pixels(image.resize(size),original[offset])
    result=bytearray(original)
    assert offset+16+len(pixels)<=len(result)
    result[offset+16:offset+16+len(pixels)]=pixels
    return bytes(result)
