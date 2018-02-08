#!/usr/bin/python3
#
# Copyright 2017 The Board of Trustees of the Leland Stanford Junior University
#
# Author: Giovanni Campagna <gcampagn@cs.stanford.edu>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
Created on Dec 20, 2017

@author: gcampagn
'''

import os
import sys
import numpy as np

from models import Config
from util.loader import load_data, unknown_tokens

def run():
    if len(sys.argv) < 3:
        print("** Usage: python3 " + sys.argv[0] + " <<Model Directory>> <<Train Data>>")
        sys.exit(1)

    np.random.seed(42)
    
    model_dir = sys.argv[1]
    config = Config.load(['./default.conf', os.path.join(model_dir, 'model.conf')])

    # load programs
    all_programs = np.load(sys.argv[2], allow_pickle=False)

    # concatenate all programs into one vector
    all_programs = np.reshape(all_programs, (-1,))
    
    counts = np.bincount(all_programs, minlength=config.output_size)
    #config.grammar.print_all_actions()
    
    # ignore the control tokens
    for i in range(config.grammar.output_size):
        print(i, counts[i], config.grammar.output_to_string(i), sep='\t')

if __name__ == '__main__':
    run()