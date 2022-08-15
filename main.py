#!/bin/env python3
import argparse
import os
from typing import List, Optional

from code_generator import CodeGenerator
from helpers import environ_or_default


class CliArgs(object):

    def __init__(self):
        self.args: Optional[argparse.Namespace] = None
        self.parser: argparse.ArgumentParser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        output_group = self.parser.add_argument_group("Output")
        output_group.add_argument("-o", "--output",
                                  help="output file name; auto generated if empty; env: OUTPUT",
                                  default=environ_or_default("OUTPUT", ""))
        output_group.add_argument("-f", "--force",
                                  help="overwrite existing file",
                                  action="store_true")
        output_group.add_argument("-c", "--compress",
                                  help="remove comments, empty lines and strip whitespaces; env: COMPRESS",
                                  default=environ_or_default("COMPRESS", False),
                                  action="store_true")

    def parse(self):
        self.args = self.parser.parse_args()


class Exporter(object):

    def __init__(self):
        c = CliArgs()
        self.generator = CodeGenerator(c.parser)
        c.parse()
        self.args = c.args
        self.generator.setup(self.args)

    def compress(self, lines: List[str]) -> List[str]:
        if not self.args.compress:
            return lines

        stripped = [line.strip() for line in lines]
        without_comments = [line for line in stripped if not line.startswith(";")]
        return [line for line in without_comments if len(line) > 0]

    def run(self):
        if os.path.exists(self.args.output) and not self.args.force:
            print(f"failed to write file '{self.args.output}', file already exists")
            exit(1)

        file_name = self.generator.suggested_file_name if len(self.args.output) <= 0 else self.args.output
        with open(file_name, mode="w") as f:
            f.write("\n".join(self.compress(self.generator.get_preamble())) + "\n")
            f.write("\n".join(self.compress(self.generator.get_program())) + "\n")
            f.write("\n".join(self.compress(self.generator.get_postamble())) + "\n")
            f.close()
            print(f"exported {os.stat(f.name).st_size} bytes g-code to file '{file_name}' using generator '{self.generator.name}' ({self.generator.description})")


if __name__ == "__main__":
    Exporter().run()
