import argparse

import pytest


@pytest.fixture
def subparser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true', help='Enable exception traces')
    return parser.add_subparsers(dest='command', help='Commands')


def test_packer_instance(subparser):
    from ttblit.tool import packer

    packer.Packer(subparser)


def test_cmake_instance(subparser):
    from ttblit.tool import cmake

    cmake.CMake(subparser)


def test_flasher_instance(subparser):
    from ttblit.tool import flasher

    flasher.Flasher(subparser)


def test_image_instance(subparser):
    from ttblit.asset.builders import image

    image.ImageAsset(subparser)


def test_raw_instance(subparser):
    from ttblit.asset.builders import raw

    raw.RawAsset(subparser)


def test_map_instance(subparser):
    from ttblit.asset.builders import map

    map.MapAsset(subparser)
