#!/bin/bash
# $1==SEED_BASIS  
# $2==ARCH( /BN+CNN3x3)
# $3==NBR_DISTRACTORS (192 train + 64 test)
# $4==BATCH_SIZE (8/48/96/144/192)

python train.py --seed $(($1+0)) \
--arch $2 \
--epoch 10000 \
--distractor_sampling uniform \
--nbr_train_distractors $3 --nbr_test_distractors $3 \
--max_sentence_length 20 --vocab_size 100 \
--dataset dSprites \
--train_test_split_strategy combinatorial2-Y-2-2-X-2-2-Orientation-40-N-Scale-6-N-Shape-3-N \
--use_cuda \
--batch_size $4 &
#--shared_architecture \
#--fast \


python train.py --seed $(($1+10)) \
--arch $2 \
--epoch 10000 \
--distractor_sampling uniform \
--nbr_train_distractors $3 --nbr_test_distractors $3 \
--max_sentence_length 20 --vocab_size 100 \
--dataset dSprites \
--train_test_split_strategy combinatorial2-Y-2-2-X-2-2-Orientation-40-N-Scale-6-N-Shape-3-N \
--use_cuda \
--batch_size $4 &
#--shared_architecture \
#--fast \


python train.py --seed $(($1+20)) \
--arch $2 \
--epoch 10000 \
--distractor_sampling uniform \
--nbr_train_distractors $3 --nbr_test_distractors $3 \
--max_sentence_length 20 --vocab_size 100 \
--dataset dSprites \
--train_test_split_strategy combinatorial2-Y-2-2-X-2-2-Orientation-40-N-Scale-6-N-Shape-3-N \
--use_cuda \
--batch_size $4 &
#--shared_architecture \
#--fast \


python train.py --seed $(($1+30)) \
--arch $2 \
--epoch 10000 \
--distractor_sampling uniform \
--nbr_train_distractors $3 --nbr_test_distractors $3 \
--max_sentence_length 20 --vocab_size 100 \
--dataset dSprites \
--train_test_split_strategy combinatorial2-Y-2-2-X-2-2-Orientation-40-N-Scale-6-N-Shape-3-N \
--use_cuda \
--batch_size $4 &
#--shared_architecture \
#--fast \


python train.py --seed $(($1+40)) \
--arch $2 \
--epoch 10000 \
--distractor_sampling uniform \
--nbr_train_distractors $3 --nbr_test_distractors $3 \
--max_sentence_length 20 --vocab_size 100 \
--dataset dSprites \
--train_test_split_strategy combinatorial2-Y-2-2-X-2-2-Orientation-40-N-Scale-6-N-Shape-3-N \
--use_cuda \
--batch_size $4 &
#--shared_architecture \
#--fast \
