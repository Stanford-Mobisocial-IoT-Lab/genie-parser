#!/usr/bin/python3
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
Created on Apr 30, 2018

@author: gcampagn
'''

import sys
from grammar.thingtalk import ThingTalkGrammar
import csv

def main():
    writer = csv.DictWriter(sys.stdout, ('sentence_length', 'gold_length', 'gold_num_prod', 
                                         'num_total_params', 'num_total_filters', 'num_params', 'num_filters', 'param_comb',
                                         'ok', 'ok_grammar', 'ok_function', 'ok_fn_count', 'ok_signature'))
    writer.writeheader()
    grammar = ThingTalkGrammar(sys.argv[1], quiet=True)
    device = '@' + sys.argv[2] if len(sys.argv) >= 3 else None
    
    for line in sys.stdin:
        sentence, gold, predicted, ok, ok_grammar, ok_function, ok_fn_count, ok_signature = line.strip().split('\t')
        assert ok in ('True', 'False')
        assert ok_grammar in ('CorrectGrammar', 'IncorrectGrammar')
        assert ok_function in ('CorrectFunction', 'IncorrectFunction')
        assert ok_fn_count in ('CorrectNumFunction', 'IncorrectNumFunction')
        assert ok_signature in ('CorrectSignature', 'IncorrectSignature')

        num_total_params = 0
        num_total_filters = 0
        num_params = 0
        num_filters = 0
        gold = gold.split(' ')
        in_device = device is None
        in_filter = False

        param_comb = []
        for token in gold:
            if device is not None:
                if token.startswith(device):
                    in_device = True
                elif token.startswith('@'):
                    in_device = False
            if token.startswith('@') or token == ')':
                in_filter = False
            elif token == 'filter':
                in_filter = True
            elif token.startswith('param:'):
                if in_device:
                    param_comb.append(token)
                if in_filter:
                    num_total_filters += 1
                    if in_device:
                        num_filters += 1
                else:
                    num_total_params += 1
                    if in_device:
                        num_params += 1

        vector, length = grammar.vectorize_program(gold, max_length=60)
        
        writer.writerow({
            'sentence_length': len(sentence.split(' ')),
            'gold_length': len(gold),
            'gold_num_prod': length,
            'num_total_params': num_total_params,
            'num_total_filters': num_total_filters,
            'num_params': num_params,
            'num_filters': num_filters,
            'param_comb': ' '.join(param_comb),
            'ok': 1 if ok == 'True' else 0,
            'ok_grammar': 1 if ok_grammar == 'CorrectGrammar' else 0,
            'ok_function': 1 if ok_function == 'CorrectFunction' else 0,
            'ok_fn_count': 1 if ok_fn_count == 'CorrectNumFunction' else 0,
            'ok_signature': 1 if ok_signature == 'CorrectSignature' else 0
        })

if __name__ == '__main__':
    main()