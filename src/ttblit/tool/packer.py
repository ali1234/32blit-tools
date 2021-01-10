import logging
import pathlib

import yaml

from ..asset.builder import AssetBuilder, make_symbol_name
from ..asset.writer import AssetWriter
from ..core.tool import Tool


class Packer(Tool):
    command = 'pack'
    help = 'Pack a collection of assets for 32Blit'

    def __init__(self, parser):
        Tool.__init__(self, parser)
        self.parser.add_argument('--config', type=pathlib.Path, help='Asset config file')
        self.parser.add_argument('--output', type=pathlib.Path, help='Name for output file(s) or root path when using --config')
        self.parser.add_argument('--files', nargs='+', type=pathlib.Path, help='Input files')
        self.parser.add_argument('--force', action='store_true', help='Force file overwrite')

        self.config = {}
        self.targets = []
        self.general_options = {}

    def parse_config(self, config_file):
        config = open(config_file).read()
        config = yaml.safe_load(config)

        self.config = config

    def filelist_to_config(self, filelist, output):
        config = {}

        for file in filelist:
            config[file] = {}

        self.config = {f'{output}': config}

    def get_general_options(self):
        for key, value in self.config.items():
            if key in ():
                self.general_options[key] = value

        for key, value in self.general_options.items():
            self.config.items.pop(key)

    def run(self, args):
        self.working_path = pathlib.Path('.')

        if args.config is not None:
            if args.config.is_file():
                self.working_path = args.config.parent
            else:
                logging.warning(f'Unable to find config at {args.config}')

        if args.output is not None:
            self.destination_path = args.output
        else:
            self.destination_path = self.working_path

        if args.config is not None:
            self.parse_config(args.config)
            logging.info(f'Using config at {args.config}')

        elif args.files is not None and args.output is not None:
            self.filelist_to_config(args.files, args.output)

        self.get_general_options()

        # Top level of our config is filegroups and general settings
        for target, options in self.config.items():
            output_file = self.working_path / target
            logging.info(f'Preparing output target {output_file}')

            asset_sources = []
            target_options = {}

            for key, value in options.items():
                if key in ('prefix', 'type'):
                    target_options[key] = value

            # Strip high-level options from the dict
            # Leaving just file source globs
            for key in target_options:
                options.pop(key)

            for file_glob, file_options in options.items():
                # Treat the input string as a glob, and get an input filelist
                if type(file_glob) is str:
                    input_files = list(self.working_path.glob(file_glob))
                else:
                    input_files = [file_glob]
                if len(input_files) == 0:
                    logging.warning(f'Input file(s) not found {self.working_path / file_glob}')
                    continue

                # Rewrite a single string option to `name: option`
                # This handles: `inputfile.bin: filename` entries
                if type(file_options) is str:
                    file_options = {'name': file_options}

                elif file_options is None:
                    file_options = {}

                # Handle both an array of options dicts or a single dict
                if type(file_options) is not list:
                    file_options = [file_options]

                for file_opts in file_options:
                    asset_sources.append((input_files, file_opts))

            self.targets.append((
                output_file,
                asset_sources,
                target_options
            ))

        self.destination_path.mkdir(parents=True, exist_ok=True)

        for path, sources, options in self.targets:
            aw = AssetWriter()
            for input_files, file_opts in sources:
                for asset in build_assets(input_files, self.working_path, file_opts, prefix=options.get('prefix')):
                    aw.add_asset(*asset)

            aw.write(options.get('type'), self.destination_path / path.name, force=args.force)


def build_assets(input_files, working_path, builder_options, typestr=None, prefix=None):
    if typestr is None:
        # Glob files all have the same suffix, so we only care about the first one
        try:
            typestr = AssetBuilder.guess_builder(input_files[0])
        except TypeError:
            logging.warning(f'Unable to guess type, assuming raw/binary {input_files[0]}.')
            typestr = 'raw/binary'

    input_type, input_subtype = typestr.split('/')
    builder = AssetBuilder._by_name[input_type]

    # Now we know our target builder, one last iteration through the options
    # allows some pre-processing stages to remap paths or other idiosyncrasies
    # of the yml config format.
    # Currently the only option we need to do this on is 'palette' for images.
    for option in ['palette']:
        try:
            if not pathlib.Path(builder_options[option]).is_absolute():
                builder_options[option] = working_path / builder_options[option]
        except KeyError:
            pass

    for file in input_files:
        symbol_name = make_symbol_name(
            base=builder_options.get('name', None), working_path=working_path, input_file=file,
            input_type=input_type, input_subtype=input_subtype, prefix=prefix
        )

        yield symbol_name, builder.from_file(file, input_subtype, **builder_options)
        logging.info(f' - {typestr} {file} -> {symbol_name}')
