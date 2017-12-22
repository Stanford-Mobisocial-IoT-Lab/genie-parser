# Copyright 2017 Giovanni Campagna <gcampagn@cs.stanford.edu
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
Created on Jul 25, 2017

@author: gcampagn
'''

import tensorflow as tf

from .base_aligner import BaseAligner
from . import common

from tensorflow.contrib.seq2seq import LuongAttention, AttentionWrapper
from tensorflow.contrib.seq2seq import BasicDecoder, \
    TrainingHelper, GreedyEmbeddingHelper
from tensorflow.python.util import nest

class Seq2SeqAligner(BaseAligner):
    '''
    A model that implements Seq2Seq: that is, it uses a sequence loss
    during training, and a greedy decoder during inference 
    '''
    
    def add_decoder_op(self, enc_final_state, enc_hidden_states, output_embed_matrix, training):
        cell_dec = common.make_multi_rnn_cell(self.config.rnn_layers, self.config.rnn_cell_type,
                                              self.config.decoder_hidden_size, self.dropout_placeholder)
        
        encoder_hidden_size = int(enc_hidden_states.get_shape()[-1])
        decoder_hidden_size = int(cell_dec.output_size)
        
        # if encoder and decoder have different sizes, add a projection layer
        if encoder_hidden_size != decoder_hidden_size:
            assert False, (encoder_hidden_size, decoder_hidden_size)
            with tf.variable_scope('hidden_projection'):
                kernel = tf.get_variable('kernel', (encoder_hidden_size, decoder_hidden_size), dtype=tf.float32)
            
                # apply a relu to the projection for good measure
                enc_final_state = nest.map_structure(lambda x: tf.nn.relu(tf.matmul(x, kernel)), enc_final_state)
                enc_hidden_states = tf.nn.relu(tf.tensordot(enc_hidden_states, kernel, [[2], [1]]))
        else:
            # flatten and repack the state
            enc_final_state = nest.pack_sequence_as(cell_dec.state_size, nest.flatten(enc_final_state))
        
        if self.config.connect_output_decoder:
            cell_dec = common.ParentFeedingCellWrapper(cell_dec, enc_final_state)
        else:
            cell_dec = common.InputIgnoringCellWrapper(cell_dec, enc_final_state)
        if self.config.apply_attention:
            input_length = tf.shape(self.input_placeholder)[1]
            
            if self.config.attention_probability_fn == 'softmax':
                probability_fn = tf.nn.softmax
                score_mask_value = float('-inf')
            elif self.config.attention_probability_fn == 'hardmax':
                probability_fn = tf.contrib.seq2seq.hardmax
                score_mask_value = float('-inf')
            elif self.config.attention_probability_fn == 'sparsemax':
                def sparsemax(originalattentionscores):
                    originalshape = tf.shape(originalattentionscores)
                    attentionscores = tf.reshape(originalattentionscores, (self.batch_size, input_length))
                    attentionscores = tf.contrib.sparsemax.sparsemax(attentionscores)
                    with tf.control_dependencies([tf.verify_tensor_all_finite(originalattentionscores, 'what'),
                                                  tf.assert_non_negative(attentionscores),
                                                  tf.assert_less_equal(attentionscores, 1., summarize=60)]):
                        return tf.reshape(attentionscores, originalshape)
                probability_fn = sparsemax
                # sparsemax does not deal with -inf properly, and has significant numerical stability issues
                # with large numbers (positive or negative)
                score_mask_value = -1e+5
            else:
                raise ValueError("Invalid attention_probability_fn " + str(self.config.attention_probability_fn))
            
            with tf.variable_scope('attention', initializer=tf.initializers.identity(dtype=tf.float32)):
                attention = LuongAttention(self.config.decoder_hidden_size, enc_hidden_states, self.input_length_placeholder,
                                           probability_fn=probability_fn, score_mask_value=score_mask_value)
            cell_dec = AttentionWrapper(cell_dec, attention,
                                        cell_input_fn=lambda inputs, _: inputs,
                                        attention_layer_size=self.config.decoder_hidden_size,
                                        alignment_history=True,
                                        initial_cell_state=enc_final_state)
            enc_final_state = cell_dec.zero_state(self.batch_size, dtype=tf.float32)
        
        go_vector = tf.ones((self.batch_size,), dtype=tf.int32) * self.config.grammar.start
        if training:
            output_ids_with_go = tf.concat([tf.expand_dims(go_vector, axis=1), self.output_placeholder], axis=1)
            outputs = tf.nn.embedding_lookup([output_embed_matrix], output_ids_with_go)
            helper = TrainingHelper(outputs, self.output_length_placeholder+1)
        else:
            helper = GreedyEmbeddingHelper(output_embed_matrix, go_vector, self.config.grammar.end)
        
        if self.config.use_dot_product_output:
            output_layer = common.DotProductLayer(output_embed_matrix)
        else:
            output_layer = tf.layers.Dense(self.config.grammar.output_size, use_bias=False)
        
        decoder = BasicDecoder(cell_dec, helper, enc_final_state, output_layer=output_layer)
        final_outputs, final_state, _ = tf.contrib.seq2seq.dynamic_decode(decoder,
                                                                          impute_finished=True,
                                                                          maximum_iterations=self.config.max_length,
                                                                          swap_memory=True)
        if self.config.apply_attention:
            # convert alignment history from time-major to batch major
            self.attention_scores = tf.transpose(final_state.alignment_history.stack(), [1, 0, 2])
        return final_outputs
        
    def finalize_predictions(self, preds):
        # add a dimension of 1 between the batch size and the sequence length to emulate a beam width of 1 
        return tf.expand_dims(preds.sample_id, axis=1)
    
    def add_loss_op(self, result):
        logits = result.rnn_output
        with tf.control_dependencies([tf.assert_positive(tf.shape(logits)[1], data=[tf.shape(logits)])]):
            length_diff = tf.reshape(self.config.max_length - tf.shape(logits)[1], shape=(1,))
        padding = tf.reshape(tf.concat([[0, 0, 0], length_diff, [0, 0]], axis=0), shape=(3, 2))
        preds = tf.pad(logits, padding, mode='constant')
        
        # add epsilon to avoid division by 0
        preds = preds + 1e-5

        mask = tf.sequence_mask(self.output_length_placeholder, self.config.max_length, dtype=tf.float32)
        loss = tf.contrib.seq2seq.sequence_loss(preds, self.output_placeholder, mask)

        with tf.control_dependencies([tf.assert_non_negative(loss, data=[preds, mask])]):
            return tf.identity(loss)
