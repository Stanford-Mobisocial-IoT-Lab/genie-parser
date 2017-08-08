'''
Created on Jul 20, 2017

@author: gcampagn
'''

import tensorflow as tf

from .base_model import BaseModel
from .encoders import RNNEncoder, BagOfWordsEncoder

from .config import Config
from models.tree_encoder import TreeEncoder

class BaseAligner(BaseModel):
    '''
    The base class for encoder-decoder based models for semantic parsing.
    One such model is Seq2Seq. Another model is Beam Search with Beam Training.
    '''
    
    def build(self):
        self.add_placeholders()
        
        
        xavier = tf.contrib.layers.xavier_initializer(seed=1234)
        inputs, output_embed_matrix = self.add_input_op()
        
        # the encoder
        with tf.variable_scope('RNNEnc', initializer=xavier):
            enc_hidden_states, enc_final_state = self.add_encoder_op(inputs=inputs)
            
        # the training decoder
        with tf.variable_scope('RNNDec', initializer=xavier):
            train_preds = self.add_decoder_op(enc_final_state=enc_final_state, enc_hidden_states=enc_hidden_states, output_embed_matrix=output_embed_matrix, training=True)
        self.loss = self.add_loss_op(train_preds) + self.add_regularization_loss()
        self.train_op = self.add_training_op(self.loss)
        
        # the inference decoder
        with tf.variable_scope('RNNDec', initializer=xavier, reuse=True):
            eval_preds = self.add_decoder_op(enc_final_state=enc_final_state, enc_hidden_states=enc_hidden_states, output_embed_matrix=output_embed_matrix, training=False)
        self.pred = self.finalize_predictions(eval_preds)
        self.eval_loss = self.add_loss_op(eval_preds)
    
    def add_placeholders(self):
        # batch size x number of words in the sentence
        self.add_input_placeholders()
        self.add_output_placeholders()
        self.add_extra_placeholders()
        
    def add_input_placeholders(self):
        self.input_placeholder = tf.placeholder(tf.int32, shape=(None, self.config.max_length))
        self.input_length_placeholder = tf.placeholder(tf.int32, shape=(None,))
        self.constituency_parse_placeholder = tf.placeholder(tf.bool, shape=(None, 2*self.config.max_length-1))
        
    def add_output_placeholders(self):
        self.output_placeholder = tf.placeholder(tf.int32, shape=(None, self.config.max_length))
        self.output_length_placeholder = tf.placeholder(tf.int32, shape=(None,))
        
    def add_extra_placeholders(self):
        self.batch_number_placeholder = tf.placeholder(tf.int32, shape=())
        self.dropout_placeholder = tf.placeholder(tf.float32, shape=())

    def create_feed_dict(self, inputs_batch, input_length_batch, parses_batch, labels_batch=None, label_length_batch=None, dropout=1, batch_number=0):
        feed_dict = dict()
        feed_dict[self.input_placeholder] = inputs_batch
        feed_dict[self.input_length_placeholder] = input_length_batch
        feed_dict[self.constituency_parse_placeholder] = parses_batch
        if labels_batch is not None:
            feed_dict[self.output_placeholder] = labels_batch
        if label_length_batch is not None:
            feed_dict[self.output_length_placeholder] = label_length_batch
        feed_dict[self.dropout_placeholder] = dropout
        feed_dict[self.batch_number_placeholder] = batch_number
        return feed_dict
    
    def make_rnn_cell(self, id):
        if self.config.rnn_cell_type == "lstm":
            cell = tf.contrib.rnn.LSTMCell(self.config.hidden_size)
        elif self.config.rnn_cell_type == "gru":
            cell = tf.contrib.rnn.GRUCell(self.config.hidden_size)
        elif self.config.rnn_cell_type == "basic-tanh":
            cell = tf.contrib.rnn.BasicRNNCell(self.config.hidden_size)
        else:
            raise ValueError("Invalid RNN Cell type")
        cell = tf.contrib.rnn.DropoutWrapper(cell, output_keep_prob=self.dropout_placeholder, seed=8 + 33 * id)
        return cell

    def add_encoder_op(self, inputs):
        if self.config.encoder_type == "rnn":
            encoder = RNNEncoder(cell_type=self.config.rnn_cell_type, embed_size=self.config.embed_size, output_size=self.config.hidden_size,
                                 dropout=self.dropout_placeholder, num_layers=self.config.rnn_layers)
        elif self.config.encoder_type == "bagofwords":
            encoder = BagOfWordsEncoder(cell_type=self.config.rnn_cell_type, embed_size=self.config.embed_size, output_size=self.config.hidden_size,
                                        dropout=self.dropout_placeholder)
        elif self.config.encoder_type == "tree":
            encoder = TreeEncoder(cell_type=self.config.rnn_cell_type, embed_size=self.config.embed_size, output_size=self.config.hidden_size,
                                  dropout=self.dropout_placeholder, num_layers=self.config.rnn_layers, max_time=self.config.max_length)
        else:
            raise ValueError("Invalid encoder type")
        return encoder.encode(inputs, self.input_length_placeholder, self.constituency_parse_placeholder)

    @property
    def batch_size(self):
        return tf.shape(self.input_placeholder)[0]

    def add_input_op(self):
        with tf.variable_scope('embed'):
            # first the embed the input
            if self.config.train_input_embeddings:
                if self.config.input_embedding_matrix:
                    initializer = tf.constant_initializer(self.config.input_embedding_matrix)
                else:
                    initializer = tf.get_variable_scope().initializer
                input_embed_matrix = tf.get_variable('input_embedding',
                                                     shape=(self.config.dictionary_size, self.config.embed_size),
                                                     initializer=initializer)  
            else:
                input_embed_matrix = tf.constant(self.config.input_embedding_matrix)

            # dictionary size x embed_size
            assert input_embed_matrix.get_shape() == (self.config.dictionary_size, self.config.embed_size)

            # now embed the output
            if self.config.train_output_embeddings:
                output_embed_matrix = tf.get_variable('output_embedding',
                                                      shape=(self.config.output_size, self.config.output_embed_size),
                                                      initializer=tf.constant_initializer(self.config.output_embedding_matrix))
            else:
                output_embed_matrix = tf.constant(self.config.output_embedding_matrix)
                
            assert output_embed_matrix.get_shape() == (self.config.output_size, self.config.output_embed_size)

        inputs = tf.nn.embedding_lookup([input_embed_matrix], self.input_placeholder)
        # batch size x max length x embed_size
        assert inputs.get_shape()[1:] == (self.config.max_length, self.config.embed_size)
        return inputs, output_embed_matrix
    
    def add_decoder_op(self, enc_final_state, enc_hidden_states, output_embed_matrix, training):
        raise NotImplementedError()

    def add_regularization_loss(self):
        weights = [w for w in tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES) if w.name.split('/')[-1] in ('kernel:0', 'weights:0')]
        
        if self.config.l2_regularization == 0.0:
            return 0

        return tf.contrib.layers.apply_regularization(tf.contrib.layers.l2_regularizer(self.config.l2_regularization), weights)

    def add_loss_op(self, preds):
        raise NotImplementedError()

    def add_training_op(self, loss):
        #optimizer = tf.train.AdamOptimizer(self.config.lr)
        #optimizer = tf.train.AdagradOptimizer(self.config.lr)
        optclass = getattr(tf.train, self.config.optimizer + 'Optimizer')
        assert issubclass(optclass, tf.train.Optimizer)
        optimizer = optclass(self.config.learning_rate)

        gradient_var_pairs = optimizer.compute_gradients(loss)
        vars = [x[1] for x in gradient_var_pairs]
        gradients = [x[0] for x in gradient_var_pairs]
        if self.config.gradient_clip > 0:
            clipped, _ = tf.clip_by_global_norm(gradients, self.config.gradient_clip)
        else:
            clipped = gradients

        self.grad_norm = tf.global_norm(clipped)
        train_op = optimizer.apply_gradients(zip(clipped, vars))
        return train_op

    def __init__(self, config : Config):
        self.config = config
