from ..builder import AssetBuilder, AssetTool

raw_typemap = {
    'binary': {
        '.bin': True,
        '.raw': True,
    },
    'csv': {
        '.csv': True
    }
}


def csv_to_binary(data, base=10, offset=0):
    try:
        data = data.decode('utf-8')
    except AttributeError:
        pass

    data = data.strip()

    # Replace '1, 2, 3' to '1,2,3', might as well do it here
    data = data.replace(' ', '')

    # Split out into rows on linebreak
    data = data.split('\n')

    # Split every row into columns on the comma
    data = [row.split(',') for row in data]

    # Flatten our rows/cols 2d array into a 1d array of bytes
    # Might as well do the int conversion here, to save another loop
    data = [(int(col, base) + offset) for row in data for col in row if col != '']

    return bytes(data)


@AssetBuilder(typemap=raw_typemap)
def raw(data, subtype, **kwargs):
    if subtype == 'csv':
        return csv_to_binary(data, base=10)
    elif subtype == 'binary':
        return data
    else:
        raise TypeError(f'Unknown subtype {subtype} for raw.')


class RawAsset(AssetTool):
    command = 'raw'
    help = 'Convert raw/binary or csv data for 32Blit'
    builder = raw

    def to_binary(self):
        return self.builder.from_file(
            self.input_file, self.input_type
        )
