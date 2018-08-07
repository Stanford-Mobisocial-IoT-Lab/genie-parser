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
Created on Jul 20, 2017

@author: gcampagn
'''

import configparser
import importlib
import pickle

from util.loader import load_dictionary, load_embeddings
from collections import OrderedDict


def create_grammar(grammar_type, *args, **kw):
    pkg = None
    class_name = None
    
    if grammar_type in ("tt", 'new-tt'):
        pkg = 'thingtalk'
        class_name = 'ThingTalkGrammar'
    elif grammar_type in ('tt-split-device', 'new-tt-split-device'):
        pkg = 'thingtalk'
        class_name = 'ThingTalkGrammar'
        kw['split_device'] = True
    elif grammar_type == 'reverse-tt':
        pkg = 'thingtalk'
        class_name = 'ThingTalkGrammar'
        kw['reverse'] = True
    elif grammar_type == 'reverse-tt-split-device':
        pkg = 'thingtalk'
        class_name = 'ThingTalkGrammar'
        kw['reverse'] = True
        kw['split_device'] = True
    elif grammar_type == "simple":
        pkg = 'simple'
        class_name = 'SimpleGrammar'
    elif grammar_type == 'simple-split-device':
        pkg = 'simple'
        class_name = 'SimpleGrammar'
        kw['split_device'] = True
    elif grammar_type == 'django-BU':
        pkg = 'django'
        class_name = 'DjangoGrammar'
    elif grammar_type == 'django-TD':
        pkg = 'django'
        class_name = 'DjangoGrammar'
        kw['reverse'] = True
    else:
        pkg, class_name = grammar_type.rsplit('.', maxsplit=1)
    module = importlib.import_module('grammar.' + pkg)
    return getattr(module, class_name)(*args, **kw)


class Config(object):
    def __init__(self):
        self._config = configparser.ConfigParser()
        
        self._config['model'] = OrderedDict(
            model_type='seq2seq',
            encoder_type='birnn',
            encoder_hidden_size=125,
            decoder_hidden_size=250,
            rnn_cell_type='lstm',
            rnn_layers=1,
            apply_attention='true',
            attention_probability_fn='softmax'
        )
        self._config['training'] = OrderedDict(
            batch_size=256,
            n_epochs=25,
            learning_rate=0.005,
            learning_rate_decay=0.95,
            dropout=0.5,
            gradient_clip=1.0,
            l2_regularization=0.0,
            l1_regularization=0.0,
            embedding_l2_regularization=0.0,
            scheduled_sampling=0.0,
            optimizer='RMSProp',
            shuffle_data='true',
            use_margin_loss='true',
            curriculum_schedule=0.05,
            curriculum_max_prob=0.7
        )
        self._config['input'] = OrderedDict(
            input_words='./en/input_words.txt',
            input_embeddings='./en/embeddings-300.txt',
            input_embed_size=300,
            input_projection=75,
            max_length=65,
            train_input_embeddings='false',
            use_typed_embeddings='true'
        )
        self._config['output'] = OrderedDict(
            grammar='thingtalk.ThingTalkGrammar',
            grammar_input_file='./en/thingpedia.json',
            train_output_embeddings='true',
            output_embed_size=100,
            beam_width=10,
            training_beam_width=10
        )
        
        self._grammar = None
        self._words = None
        self._reverse = None
        self._embeddings_matrix = None
        self._output_embeddings_matrix = None
        self._input_embed_size = 0
            
    @property
    def model_type(self):
        return self._config['model']['model_type']
    
    @property
    def encoder_type(self):
        return self._config['model']['encoder_type']
    
    @property
    def max_length(self):
        return int(self._config['input']['max_length'])
    
    @property
    def dropout(self):
        return float(self._config['training']['dropout'])
    
    @property
    def input_embed_size(self):
        return self._input_embed_size
    
    @property
    def input_projection(self):
        return int(self._config['input']['input_projection'])
    
    @property
    def output_embed_size(self):
        if self.train_output_embeddings:
            return int(self._config['output']['output_embed_size'])
        elif isinstance(self._output_embeddings_matrix, dict):
            sizes = dict()
            for key, matrix in self._output_embeddings_matrix.items():
                sizes[key] = matrix.shape[1]
            return sizes
        else:
            return self._output_embeddings_matrix.shape[1]
        
    @property
    def output_size(self):
        return self._grammar.output_size
        
    @property
    def encoder_hidden_size(self):
        model_conf = self._config['model']
        if 'hidden_size' in model_conf:
            return int(model_conf['hidden_size'])
        else:
            return int(model_conf['encoder_hidden_size'])
        
    @property
    def decoder_hidden_size(self):
        model_conf = self._config['model']
        if 'hidden_size' in model_conf:
            return int(model_conf['hidden_size'])
        else:
            return int(model_conf['decoder_hidden_size'])
    
    @property
    def scheduled_sampling(self):
        return float(self._config['training']['scheduled_sampling'])
    
    @property
    def batch_size(self):
        return int(self._config['training']['batch_size'])
    
    @property
    def beam_size(self):
        if self._config['model']['model_type'] in ('beamsearch','beamdecode'):
            return int(self._config['output']['beam_width'])
        else:
            return 1
        
    @property
    def training_beam_size(self):
        if self._config['model']['model_type'] == 'beamsearch':
            return int(self._config['output']['training_beam_width'])
        else:
            return 1
        
    @property
    def n_epochs(self):
        return int(self._config['training']['n_epochs'])
    
    @property
    def learning_rate(self):
        return float(self._config['training']['learning_rate'])

    @property
    def learning_rate_decay(self):
        return float(self._config['training']['learning_rate_decay'])

    @property
    def gradient_clip(self):
        return float(self._config['training']['gradient_clip'])
    
    @property
    def l2_regularization(self):
        return float(self._config['training']['l2_regularization'])

    @property
    def l1_regularization(self):
        return float(self._config['training']['l1_regularization'])

    @property
    def embedding_l2_regularization(self):
        return float(self._config['training']['embedding_l2_regularization'])

    @property
    def optimizer(self):
        return self._config['training']['optimizer']

    @property
    def shuffle_training_data(self):
        return self._config['training'].getboolean('shuffle_data')

    @property
    def use_margin_loss(self):
        return self._config['training'].getboolean('use_margin_loss')

    @property
    def curriculum_schedule(self):
        return float(self._config['training']['curriculum_schedule'])

    @property
    def curriculum_max_prob(self):
        return float(self._config['training']['curriculum_max_prob'])
    
    @property
    def train_input_embeddings(self):
        return self._config['input'].getboolean('train_input_embeddings')
    
    @property
    def typed_input_embeddings(self):
        return self._config['input'].getboolean('use_typed_embeddings')
    
    @property
    def train_output_embeddings(self):
        return self._config['output'].getboolean('train_output_embeddings')
    
    @property
    def rnn_cell_type(self):
        return self._config['model']['rnn_cell_type']
    
    @property
    def rnn_layers(self):
        return int(self._config['model']['rnn_layers'])
    
    @property
    def apply_attention(self):
        return self._config['model'].getboolean('apply_attention')
    
    @property
    def attention_probability_fn(self):
        return self._config['model']['attention_probability_fn']
    
    @property
    def grammar(self):
        return self._grammar
    
    @property
    def dictionary_size(self):
        return len(self._words)
    
    @property
    def dictionary(self):
        return self._words

    @property
    def reverse_dictionary(self):
        return self._reverse

    @property
    def input_embedding_matrix(self):
        return self._embeddings_matrix
    
    @property
    def output_embedding_matrix(self):
        return self._output_embeddings_matrix
        
    def save(self, filename):
        with open(filename, 'w') as fp:
            self._config.write(fp)
        
    @staticmethod
    def load(filenames, load_grammar=False, cached_grammar=None):
        self = Config()
        print('Loading configuration from', filenames)
        self._config.read(filenames)
        self._input_embed_size = int(self._config['input']['input_embed_size'])
        
        flatten_grammar = self.model_type != 'extensible'

        if load_grammar:
            with open(cached_grammar, 'rb') as fp:
                self._grammar = pickle.load(fp)
        else:
            self._grammar = create_grammar(self._config['output']['grammar'],
                                           self._config['output']['grammar_input_file'],
                                           flatten=flatten_grammar,
                                           max_input_length=self.max_length)

        words, reverse = load_dictionary(self._config['input']['input_words'],
                                         use_types=self.typed_input_embeddings,
                                         grammar=self._grammar)
        if not load_grammar:
            self._grammar.set_input_dictionary(words)
            if cached_grammar is not None:
                with open(cached_grammar, 'wb') as fp:
                    pickle.dump(self._grammar, fp, pickle.HIGHEST_PROTOCOL)

        self._words = words
        self._reverse = reverse
        print("%d words in dictionary" % (self.dictionary_size,))
        for key, size in self.output_size.items():
            print("%d %s output tokens" % (size, key))

        if self._config['input']['input_embeddings'] == 'xavier':
            assert self.train_input_embeddings
            assert not self.typed_input_embeddings
            self._embeddings_matrix = None
        else:
            self._embeddings_matrix, self._input_embed_size = load_embeddings(self._config['input']['input_embeddings'],
                                                                              words,
                                                                              use_types=self.typed_input_embeddings,
                                                                              grammar=self._grammar,
                                                                              embed_size=self._input_embed_size)
        print("Input embed size", self._input_embed_size)
        
        if self._config['output'].get('output_embeddings', None):
            self._output_embeddings_matrix, _ = load_embeddings(self._config['output']['output_embeddings'],
                                                                self._grammar.dictionary,
                                                                use_types=False, grammar=None,
                                                                embed_size=int(self._config['output']['output_embed_size']))
        else:
            self._output_embeddings_matrix = self._grammar.get_embeddings(words, self._embeddings_matrix)
        print("Output embed size", self.output_embed_size)

        return self