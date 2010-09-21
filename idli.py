#!/usr/bin/python

## Idli - a command line bug tracker interface
## Copyright (C) 2010 Chris Stucchio
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.


import idli
import idli.commands as cmds

import sys
import argparse

if __name__ == "__main__":
    from idli.backends import get_backend_or_fail
    cmds.run_command()



