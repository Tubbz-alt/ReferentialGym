:: %1==SEED_BASIS  
:: %2==ARCH( /BN+CNN3x3)
:: %3==NBR_DISTRACTORS_TRAIN (48 train + 16 test)
:: %4==NBR_DISTRACTORS_TEST (48 train + 16 test)
:: %5==VOCAB_SIZE (5/20)
:: %6==BATCH_SIZE (2/12/24/36/48)

set /a seed = %1
start /b python train_attention.py --seed %seed% ^
--agent_type AttentionListener ^
--arch %2 ^
--epoch 10000 ^
--distractor_sampling uniform ^
--nbr_train_distractors %3 --nbr_test_distractors %4 ^
--max_sentence_length %5 --vocab_size 100 ^
--dataset dSprites ^
--train_test_split_strategy combinatorial2-Y-4-2-X-4-2-Orientation-40-N-Scale-6-N-Shape-3-N ^
--use_cuda ^
--batch_size %6 
::--shared_architecture ^
::--fast ^
::--transcoder_visual_encoder_use_coord4 ^

set /a seed = %1+10
start /b python train_attention.py --seed %seed% ^
--agent_type AttentionListener ^
--arch %2 ^
--epoch 10000 ^
--distractor_sampling uniform ^
--nbr_train_distractors %3 --nbr_test_distractors %4 ^
--max_sentence_length %5 --vocab_size 100 ^
--dataset dSprites ^
--train_test_split_strategy combinatorial2-Y-4-2-X-4-2-Orientation-40-N-Scale-6-N-Shape-3-N ^
--use_cuda ^
--batch_size %6 
::--shared_architecture ^
::--fast ^


set /a seed = %1+20
start /b python train_attention.py --seed %seed% ^
--agent_type AttentionListener ^
--arch %2 ^
--epoch 10000 ^
--distractor_sampling uniform ^
--nbr_train_distractors %3 --nbr_test_distractors %4 ^
--max_sentence_length %5 --vocab_size 100 ^
--dataset dSprites ^
--train_test_split_strategy combinatorial2-Y-4-2-X-4-2-Orientation-40-N-Scale-6-N-Shape-3-N ^
--use_cuda ^
--batch_size %6 
::--shared_architecture ^
::--fast ^


set /a seed = %1+30
start /b python train_attention.py --seed %seed% ^
--agent_type AttentionListener ^
--arch %2 ^
--epoch 10000 ^
--distractor_sampling uniform ^
--nbr_train_distractors %3 --nbr_test_distractors %4 ^
--max_sentence_length %5 --vocab_size 100 ^
--dataset dSprites ^
--train_test_split_strategy combinatorial2-Y-4-2-X-4-2-Orientation-40-N-Scale-6-N-Shape-3-N ^
--use_cuda ^
--batch_size %6 
::--shared_architecture ^
::--fast ^


set /a seed = %1+40
start /b python train_attention.py --seed %seed% ^
--agent_type AttentionListener ^
--arch %2 ^
--epoch 10000 ^
--distractor_sampling uniform ^
--nbr_train_distractors %3 --nbr_test_distractors %4 ^
--max_sentence_length %5 --vocab_size 100 ^
--dataset dSprites ^
--train_test_split_strategy combinatorial2-Y-4-2-X-4-2-Orientation-40-N-Scale-6-N-Shape-3-N ^
--use_cuda ^
--batch_size %6

::--shared_architecture ^
::--fast ^