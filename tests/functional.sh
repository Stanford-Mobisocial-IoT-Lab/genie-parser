#!/bin/bash

set -e
set -x
SRCDIR=`dirname $0`

# Functional tests
# for each combination of supported tasks and options
# create a workdir and train a model

GLOVE=${GLOVE:-glove.42B.300d.txt}
test -f $GLOVE || ( wget --no-verbose https://parmesan.stanford.edu/glove/glove.42B.300d.zip ; unzip glove.42B.300d.zip ; rm glove.42B.300d.zip )
export GLOVE

declare -A model_hparams
model_hparams[luinet_copy_transformer]=transformer_luinet
model_hparams[luinet_copy_seq2seq]=lstm_luinet



for problem in semparse_thingtalk semparse_thingtalk_noquote  ; do
    TMPDIR=`pwd`
    workdir=`mktemp -d $TMPDIR/luinet-tests-XXXXXX`
    pipenv run $SRCDIR/../luinet-datagen --problem $problem --src_data_dir $SRCDIR/dataset/$problem --data_dir $workdir --thingpedia_snapshot 6
    # retrieval model
    pipenv run python3 $SRCDIR/../luinet/scripts/retrieval.py --input_vocab $workdir/input_words.txt --thingpedia_snapshot $workdir/thingpedia.json --problem $problem --train_set $SRCDIR/dataset/$problem/train.tsv --test_set $SRCDIR/dataset/$problem/eval.tsv --cached_grammar $workdir/cached_grammar.pkl --cached_embeddings $workdir/input_embeddings.npy --train_batch_size 4

    i=0
    for model in luinet_copy_seq2seq luinet_copy_transformer ; do
        for grammar in linear bottomup ; do
            for options in "" "pointer_layer=decaying_attentive" ; do
                pipenv run $SRCDIR/../luinet-trainer --problem $problem --data_dir $workdir --output_dir $workdir/model.$i --model $model --hparams_set ${model_hparams[$model]} --hparams "grammar_direction=$grammar,$options" --export_saved_model --schedule test

                # greedy decode
                pipenv run $SRCDIR/../luinet-decoder --problem $problem --data_dir $workdir --output_dir $workdir/model.$i --model $model --hparams_set ${model_hparams[$model]} --hparams "grammar_direction=$grammar,$options" --decode_hparams 'beam_size=1,alpha=0.6'

                # beam search decode
                pipenv run $SRCDIR/../luinet-decoder --problem $problem --data_dir $workdir --output_dir $workdir/model.$i --model $model --hparams_set ${model_hparams[$model]} --hparams "grammar_direction=$grammar,$options" --decode_hparams 'beam_size=4,alpha=0.6'

                # we cannot test this until the t2t patch is merged
                #test -d $workdir/model.$i/export/best/*
                #test -f $workdir/model.$i/export/best/*/variables

                i=$((i+1))
            done
        done
    done

    for model in luinet_copy_seq2seq ; do
        for grammar in bottomup ; do
            for options in ""  ; do
                pipenv run $SRCDIR/../luinet-trainer --problem $problem --data_dir $workdir --output_dir $workdir/model.$i --model $model --hparams_set ${model_hparams[$model]} --hparams "grammar_direction=$grammar,$options" --save_checkpoints_secs 10 --eval_throttle_seconds 100 --train_steps 2 --perturb_training True --num_last_checkpoints 2 --num_loops 2
                pipenv run $SRCDIR/../luinet-decoder --problem $problem --data_dir $workdir --output_dir $workdir/model.$i/averaged_1/ --model $model --hparams_set ${model_hparams[$model]} --hparams "grammar_direction=$grammar,$options" --decode_hparams 'beam_size=1,alpha=0.6'
                pipenv run $SRCDIR/../luinet-decoder --problem $problem --data_dir $workdir --output_dir $workdir/model.$i/averaged_1/ --model $model --hparams_set ${model_hparams[$model]} --hparams "grammar_direction=$grammar,$options" --decode_hparams 'beam_size=4,alpha=0.6'

                i=$((i+1))
            done
        done
    done

    rm -fr $workdir

done