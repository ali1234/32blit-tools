from ..builder import AssetBuilder, AssetTool
from .raw import csv_to_binary

map_typemap = {
    'tiled': {
        '.tmx': True,
        '.raw': False,
    },
}


def tiled_to_binary(data):
    from xml.etree import ElementTree as ET
    root = ET.fromstring(data)
    layers = root.findall('layer/data')
    data = []
    for layer in layers:
        try:
            data.append(csv_to_binary(
                layer.text,
                base=10,
                offset=-1))  # Tiled indexes from 1 rather than 0
        except ValueError:
            raise RuntimeError(
                "Failed to convert .tmx, does it contain blank (0) tiles? Tiled is 1-indexed, so these get converted to -1 and blow everyting up")
    return b''.join(data)


@AssetBuilder(typemap=map_typemap)
def map(data, subtype, **kwargs):
    if subtype == 'tiled':
        return tiled_to_binary(data)
    else:
        raise TypeError(f'Unknown subtype {subtype} for map.')


class MapAsset(AssetTool):
    command = 'map'
    help = 'Convert popular tilemap formats for 32Blit'
    builder = map

    def to_binary(self):
        return self.builder.from_file(
            self.input_file, self.input_type
        )
