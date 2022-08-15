import argparse
from typing import Optional, List


class CodeGeneratorBase(object):

    def __init__(self, _arg_parser: argparse.ArgumentParser):
        pass

    def setup(self, args: Optional[argparse.Namespace]):
        raise NotImplementedError()

    @property
    def name(self) -> str:
        raise NotImplementedError()

    @property
    def description(self) -> str:
        raise NotImplementedError()

    def get_preamble(self) -> List[str]:
        raise NotImplementedError()

    def get_program(self) -> List[str]:
        raise NotImplementedError()

    def get_postamble(self) -> List[str]:
        raise NotImplementedError()
