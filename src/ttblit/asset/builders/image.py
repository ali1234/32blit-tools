import io
import logging
import pathlib
from math import ceil

from bitstring import BitArray
from PIL import Image

from ...core.palette import Colour, Palette, type_palette
from ...core.struct import struct_blit_image
from ..builder import AssetBuilder, AssetTool

image_typemap = {
    'image': {
        '.png': True,
        '.gif': True,
    }
}


def repetitions(seq):
    """Input: sequence of values, Output: sequence of (value, repeat count)."""
    i = iter(seq)
    prev = next(i)
    count = 1
    for v in i:
        if v == prev:
            count += 1
        else:
            yield prev, count
            prev = v
            count = 1
    yield prev, count


def rle(data, bit_length):
    """Input: data bytes, bit length, Output: RLE'd bytes"""
    # TODO: This could be made more efficient by encoding the run-length
    # as count-1, ie 0 means a run of one. Then we can encode runs of
    # length one more. But this probably needs changes in the blit engine.
    break_even = ceil(8 / (bit_length + 1))
    bits = BitArray()

    for value, count in repetitions(data):
        while count > break_even:
            chunk = min(count, 0x100)
            bits.append('0b1')
            bits.append(bytes([chunk - 1]))
            count -= chunk
            bits.append(BitArray(uint=value, length=bit_length))
        for x in range(count):
            bits.append('0b0')
            bits.append(BitArray(uint=value, length=bit_length))
    return bits.tobytes()


def quantize_image(data, palette, transparent, strict):
    if strict and len(palette) == 0:
        raise TypeError("Attempting to enforce strict colours with an empty palette, did you really want to do this?")
    # Since we already have bytes, we need to pass PIL an io.BytesIO object
    image = Image.open(io.BytesIO(data)).convert('RGBA')
    w, h = image.size
    output_image = Image.new('P', (w, h))
    for y in range(h):
        for x in range(w):
            r, g, b, a = image.getpixel((x, y))
            if transparent is not None and (r, g, b) == tuple(transparent):
                a = 0x00
            index = palette.get_entry(r, g, b, a, strict=strict)
            output_image.putpixel((x, y), index)

    return output_image


@AssetBuilder(typemap=image_typemap)
def image(data, subtype, packed=True, palette=None, transparent=None, strict=False, **kwargs):
    if palette is None:
        palette = Palette()
    elif isinstance(palette, pathlib.Path):
        palette = Palette(palette)

    image = quantize_image(data, palette, transparent, strict)

    if packed:
        bit_length = palette.bit_length()
        image_data_rl = rle(image.tobytes(), bit_length)
        image_data_pk = BitArray().join(BitArray(uint=x, length=bit_length) for x in image.tobytes()).tobytes()

        if len(image_data_pk) < len(image_data_rl):
            image_type = 'PK'
            image_data = image_data_pk
        else:
            image_type = 'RL'
            image_data = image_data_rl

    else:
        image_data = image.tobytes()
        image_type = 'RW'

    return struct_blit_image.build({
        'type': image_type,
        'width': image.size[0],
        'height': image.size[1],
        'palette_entries': len(palette),
        'palette': palette.tostruct(),
        'data': image_data
    })


class ImageAsset(AssetTool):
    command = 'image'
    help = 'Convert images/sprites for 32Blit'
    builder = image

    def __init__(self, parser=None):
        self.options.update({
            'palette': (Palette, Palette()),
            'transparent': Colour,
            'packed': (str, 'yes'),
            'strict': (bool, False)
        })

        AssetTool.__init__(self, parser)

        self.palette = None
        self.transparent = None
        self.packed = True
        self.strict = False

        if self.parser is not None:
            self.parser.add_argument('--palette', type=type_palette, default=None, help='Image or palette file of colours to use')
            self.parser.add_argument('--transparent', type=Colour, help='Transparent colour')
            self.parser.add_argument('--packed', type=str, nargs='?', default='yes', choices=('yes', 'no'), help='Pack into bits depending on palette colour count')
            self.parser.add_argument('--strict', action='store_true', help='Reject colours not in the palette')

    def prepare(self, args):
        AssetTool.prepare(self, args)

        if type(self.packed) is not bool:
            self.packed = self.packed == 'yes'

        if self.transparent is not None:
            r, g, b = self.transparent
            p = self.palette.set_transparent_colour(r, g, b)
            if p is not None:
                logging.info(f'Found transparent colour ({r},{g},{b}) in palette')
            else:
                logging.warning(f'Could not find transparent colour ({r},{g},{b}) in palette')

    def to_binary(self):
        return self.builder.from_file(
            self.input_file, self.input_type,
            packed=self.packed, palette=self.palette, transparent=self.transparent, strict=self.strict
        )
