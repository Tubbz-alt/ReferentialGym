from typing import Dict, List, Tuple
import os
import copy
import random
import time

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from tensorboardX import SummaryWriter
from tqdm import tqdm

from .agents import Speaker, Listener, ObverterAgent
from .networks import handle_nan, hasnan
from .networks import HomoscedasticMultiTasksLoss

from .datasets import collate_dict_wrapper
from .utils import cardinality, query_vae_latent_space


VERBOSE = False 


class ReferentialGame(object):
    def __init__(self, datasets, config):
        '''

        '''
        self.datasets = datasets
        self.config = config
        if 'parallel_TS_computation_max_workers' not in self.config:
            self.config['parallel_TS_computation_max_workers'] = 16

        if self.config['use_homoscedastic_multitasks_loss']:
            self.homoscedastic_mlt_loss = HomoscedasticMultiTasksLoss(use_cuda=self.config['use_cuda'])

    def _select_agents(self, it, speakers, listeners, speakers_optimizers, listeners_optimizers, agents_stats):
        idx_speaker = random.randint(0,len(speakers)-1)
        idx_listener = random.randint(0,len(listeners)-1)
            
        speaker, speaker_optimizer = speakers[idx_speaker], speakers_optimizers[idx_speaker]
        listener, listener_optimizer = listeners[idx_listener], listeners_optimizers[idx_listener]
        
        if self.config['use_cuda']:
            speaker = speaker.cuda()
            listener = listener.cuda()
        
        agents_stats[speaker.agent_id]['selection_iterations'].append(it)
        agents_stats[listener.agent_id]['selection_iterations'].append(it)

        return speaker, listener, speaker_optimizer, listener_optimizer

    def train(self, prototype_speaker: Speaker, prototype_listener: Listener, nbr_epoch: int = 10, logger: SummaryWriter = None, verbose_period=None):
        '''

        '''
        # Dataset:
        if 'batch_size' not in self.config:
            self.config['batch_size'] = 32
        if 'dataloader_num_worker' not in self.config:
            self.config['dataloader_num_worker'] = 8

        print("Create dataloader: ...")
        
        '''
        '''
        data_loaders = {'train':torch.utils.data.DataLoader(self.datasets['train'],
                                                            batch_size=self.config['batch_size'],
                                                            shuffle=True,
                                                            collate_fn=collate_dict_wrapper,
                                                            pin_memory=True,
                                                            num_workers=self.config['dataloader_num_worker']),
                        'test':torch.utils.data.DataLoader(self.datasets['test'],
                                                           batch_size=self.config['batch_size'],
                                                           shuffle=True,
                                                           collate_fn=collate_dict_wrapper,
                                                           pin_memory=True,
                                                           num_workers=self.config['dataloader_num_worker'])
                        }
        '''
        '''
        
        '''
        data_loaders = {'train':torch.utils.data.DataLoader(self.datasets['train'],
                                                    batch_size=self.config['batch_size'],
                                                    shuffle=True,
                                                    collate_fn=collate_dict_wrapper,
                                                    pin_memory=True,
                                                    num_workers=self.config['dataloader_num_worker']),
                'test':torch.utils.data.DataLoader(self.datasets['test'],
                                                   batch_size=self.config['batch_size'],
                                                   shuffle=True,
                                                   collate_fn=collate_dict_wrapper,
                                                   pin_memory=True,
                                                   num_workers=self.config['dataloader_num_worker'])
                }

        nbr_it_per_epoch = len(data_loaders['train'])
        #for epoch in tqdm(range(100)):
        for epoch in range(100):
            #print(epoch, len(data_loaders['train']))
            for i, item in tqdm(enumerate(data_loaders['train'])):
            #for i, item in enumerate(data_loaders['train']):
                #print(epoch, i)
                #print(len(item))
                pass 
        raise 
        '''

        print("Create dataloader: OK.")
        print("Create Agents: ...")
        
        # Agents:
        nbr_speaker = self.config['cultural_speaker_substrate_size']
        speakers = [prototype_speaker]+[ prototype_speaker.clone(clone_id=f's{i+1}') for i in range(nbr_speaker-1)]
        nbr_listener = self.config['cultural_listener_substrate_size']
        listeners = [prototype_listener]+[ prototype_listener.clone(clone_id=f'l{i+1}') for i in range(nbr_listener-1)]
        homoscedastic_params = []
        if self.config['use_homoscedastic_multitasks_loss']:
            homoscedastic_params = list(self.homoscedastic_mlt_loss.parameters())
        speakers_optimizers = [ optim.Adam(list(speaker.parameters())+homoscedastic_params, lr=self.config['learning_rate'], betas=(0.9, 0.999), eps=self.config['adam_eps']) for speaker in speakers ]
        listeners_optimizers = [ optim.Adam(list(listener.parameters())+homoscedastic_params, lr=self.config['learning_rate'], betas=(0.9, 0.999), eps=self.config['adam_eps']) for listener in listeners ]
        
        for name, param in prototype_speaker.named_parameters():
            print(name, param.size())
            if 'TotalCorrelationDiscriminator' in name\
            or 'tc_discriminator' in name:
                raise

        if 'meta' in self.config['cultural_reset_strategy']:
            meta_agents = dict()
            meta_agents_optimizers = dict()
            for agent in [prototype_speaker, prototype_listener]: 
                if type(agent) not in meta_agents:
                    meta_agents[type(agent)] = agent.clone(clone_id=f'meta_{agent.agent_id}')
                    #meta_agents_optimizers[type(agent)] = optim.Adam(meta_agents[type(agent)].parameters(), lr=self.config['cultural_reset_meta_learning_rate'], eps=self.config['adam_eps'])
                    meta_agents_optimizers[type(agent)] = optim.SGD(meta_agents[type(agent)].parameters(), lr=self.config['cultural_reset_meta_learning_rate'])

        agents_stats = dict()
        for agent in speakers:
            agents_stats[agent.agent_id] = {'reset_iterations':[0], 'selection_iterations':[]}
        for agent in listeners:
            agents_stats[agent.agent_id] = {'reset_iterations':[0], 'selection_iterations':[]}
        
        print("Create Agents: OK.")
        print("Launching training: ...")

        it = 0
        it_datasamples = {'train':0, 'test':0} # counting the number of data sampled from dataloaders
        it_samples = {'train':0, 'test':0} # counting the number of multi-round
        it_steps = {'train':0, 'test':0} # taking into account multi round... counting the number of sample shown to the agents.
        if self.config['use_curriculum_nbr_distractors']:
            windowed_accuracy = 0.0
            window_count = 0
            self.datasets['train'].setNbrDistractors(1)
            self.datasets['test'].setNbrDistractors(1)

        pbar = tqdm(total=nbr_epoch*len(self.datasets['train']))

        for epoch in range(nbr_epoch):
            for mode in ['train','test']:
                data_loader = data_loaders[mode]
                counterGames = 0
                total_sentences = []
                total_nbr_unique_stimulus = 0
                epoch_acc = []

                for it_dataset in range(self.config['nbr_dataset_repetition'][mode]):
                    end_of_epoch_dataset = (it_dataset==self.config['nbr_dataset_repetition'][mode]-1)
                    for idx_stimuli, sample in enumerate(data_loader):
                        end_of_epoch_datasample = end_of_epoch_dataset and (idx_stimuli==len(data_loader)-1)
                        it_datasamples[mode] += 1
                        it_datasample = it_datasamples[mode]
                        it = it_datasample
                        if mode == 'train': pbar.update(len(sample['speaker_experiences']))

                        if mode == 'train':
                            if'obverter' in self.config['graphtype']:
                                # Let us decide whether to exchange the speakers and listeners:
                                # i.e. is the round of games finished?
                                if not('obverter_nbr_games_per_round' in self.config):
                                    self.config['obverter_nbr_games_per_round'] = 1 
                                counterGames += 1
                                if  counterGames%self.config['obverter_nbr_games_per_round']==0:
                                    speakers, \
                                    listeners, \
                                    speakers_optimizers, \
                                    listeners_optimizers = (listeners, \
                                                           speakers, \
                                                           listeners_optimizers, \
                                                           speakers_optimizers)
                                if self.config['iterated_learning_scheme'] and counterGames%self.config['iterated_learning_period']==0:
                                    for lidx in range(len(listeners)):
                                        listeners[lidx].reset()
                                        print("Iterated Learning Scheme: Listener {} have just been resetted.".format(listeners[lidx].agent_id))
                                        listeners_optimizers[lidx] = optim.Adam(listeners[lidx].parameters(), 
                                            lr=self.config['learning_rate'], 
                                            eps=self.config['adam_eps'])

                        speaker, \
                        listener, \
                        speaker_optimizer, \
                        listener_optimizer = self._select_agents(it,
                                                                 speakers,
                                                                 listeners,
                                                                 speakers_optimizers,
                                                                 listeners_optimizers,
                                                                 agents_stats)
                        if mode == 'train': 
                            speaker.train()
                            listener.train()
                        else:
                            speaker.eval()
                            listener.eval()

                        if self.config['use_cuda']:
                            sample = sample.cuda()

                        # //------------------------------------------------------------//
                        # //------------------------------------------------------------//
                        # //------------------------------------------------------------//
                        
                        for it_rep in range(self.config['nbr_experience_repetition']):
                            it_samples[mode] += 1
                            it_sample = it_samples[mode]
                            end_of_epoch_sample = end_of_epoch_datasample and (it_rep==self.config['nbr_experience_repetition']-1)
                        

                            listener_sentences_one_hot = None
                            listener_sentences_widx = None 
                            batch_size = len(sample['speaker_experiences'])
                                
                            for idx_round in range(self.config['nbr_communication_round']):
                                it_steps[mode] += 1
                                it_step = it_steps[mode]

                                multi_round = True
                                if idx_round == self.config['nbr_communication_round']-1:
                                    multi_round = False
                                
                                speaker_inputs_dict = {'experiences':sample['speaker_experiences'], 
                                                       'latent_experiences':sample['speaker_latent_experiences'], 
                                                       'latent_experiences_values':sample['speaker_latent_experiences_values'], 
                                                       'sentences_one_hot':listener_sentences_one_hot,
                                                       'sentences_widx':listener_sentences_widx, 
                                                       'graphtype':self.config['graphtype'],
                                                       'tau0':self.config['tau0'],
                                                       'multi_round':multi_round,
                                                       'sample':sample,
                                                       'end_of_epoch_sample': end_of_epoch_sample
                                                       }

                                if self.config['stimulus_depth_mult'] != 1:
                                    speaker_inputs_dict['experiences'] = speaker_inputs_dict['experiences'].repeat(1, 1, 1, self.config['stimulus_depth_mult'], 1, 1)
                                    # batch_size, nbr_distractors+1, nbr_stimulus, nbr_channels, width, height
                                
                                speaker_outputs, speaker_losses = speaker.compute(inputs_dict=speaker_inputs_dict,
                                                                                config=self.config,
                                                                                role='speaker',
                                                                                mode=mode,
                                                                                it=it_step)

                                
                                listener_inputs_dict = {'graphtype':self.config['graphtype'],
                                                        'tau0':self.config['tau0'],
                                                        'multi_round':multi_round,
                                                        'sample':sample}

                                for k in speaker_outputs:
                                    listener_inputs_dict[k] = speaker_outputs[k] 

                                if self.config['graphtype'] == 'obverter':
                                    if isinstance(speaker_outputs['sentences_one_hot'], torch.Tensor):
                                        listener_inputs_dict['sentences_one_hot'] = listener_inputs_dict['sentences_one_hot'].detach()
                                    if isinstance(speaker_outputs['sentences_widx'], torch.Tensor):
                                        listener_inputs_dict['sentences_widx'] = listener_inputs_dict['sentences_widx'].detach()

                                listener_inputs_dict['experiences'] = sample['listener_experiences']
                                listener_inputs_dict['latent_experiences'] = sample['listener_latent_experiences']
                                listener_inputs_dict['latent_experiences_values'] = sample['listener_latent_experiences_values']
                                
                                if self.config['stimulus_depth_mult'] != 1:
                                    listener_inputs_dict['experiences'] = listener_inputs_dict['experiences'].repeat(1, 1, 1, self.config['stimulus_depth_mult'], 1, 1)
                                    # batch_size, nbr_distractors+1, nbr_stimulus, nbr_channels, width, height
                                
                                listener_outputs, listener_losses = listener.compute(inputs_dict=listener_inputs_dict,
                                                                                   config=self.config,
                                                                                   role='listener',
                                                                                   mode=mode,
                                                                                   it=it_step)

                                if self.config['graphtype'] == 'obverter':
                                    if isinstance(listener_outputs['sentences_one_hot'], torch.Tensor):
                                        listener_outputs['sentences_one_hot'] = listener_outputs['sentences_one_hot'].detach()
                                    if isinstance(listener_outputs['sentences_widx'], torch.Tensor):
                                        listener_outputs['sentences_widx'] = listener_outputs['sentences_widx'].detach()

                                listener_sentences_one_hot = listener_outputs['sentences_one_hot']
                                listener_sentences_widx = listener_outputs['sentences_widx']

                            # //------------------------------------------------------------//
                            # //------------------------------------------------------------//
                            # //------------------------------------------------------------//
                            
                            final_decision_logits = listener_outputs['decision']
                            
                            losses = dict()
                            losses.update(speaker_losses)
                            losses.update(listener_losses)
                            idx_loss = 1 if not self.config['use_homoscedastic_multitasks_loss'] else 2

                            if self.config['use_homoscedastic_multitasks_loss']:
                                losses = self.homoscedastic_mlt_loss(losses)
                                if logger is not None:
                                    for (lossname, lossvalues), logvar  in zip(losses.items(), self.homoscedastic_mlt_loss.homoscedastic_log_vars):
                                        logger.add_scalar('{}/HomoscedasticLogVar/{}'.format(mode, lossname), logvar.item(), it)    
                            
                            for k, v in losses.items():
                                losses[k][idx_loss] = v[0]*v[idx_loss].mean()
                            loss = sum( [l[idx_loss] for l in losses.values()])

                            if mode == 'train':
                                speaker_optimizer.zero_grad()
                                listener_optimizer.zero_grad()
                                loss.backward()
                                
                                speaker.apply(handle_nan)
                                listener.apply(handle_nan)
                                if self.config['with_gradient_clip']:
                                    nn.utils.clip_grad_value_(speaker.parameters(), self.config['gradient_clip'])
                                    nn.utils.clip_grad_value_(listener.parameters(), self.config['gradient_clip'])
                                
                                speaker_optimizer.step()
                                listener_optimizer.step()
                            

                            # //------------------------------------------------------------//
                            # //------------------------------------------------------------//
                            # //------------------------------------------------------------//
                            
                            # Compute sentences:
                            sentences = []
                            for sidx in range(batch_size):
                                sentences.append(''.join([chr(97+int(s.item())) for s in speaker_outputs['sentences_widx'][sidx] ]))
                            
                            if logger is not None:
                                if self.config['with_grad_logging'] and mode == 'train':
                                    maxgrad = 0.0
                                    for name, p in speaker.named_parameters() :
                                        if hasattr(p,'grad') and p.grad is not None:
                                            logger.add_histogram( "Speaker/{}".format(name), p.grad, idx_stimuli+len(data_loader)*epoch)
                                            cmg = torch.abs(p.grad).max()
                                            if cmg > maxgrad:
                                                maxgrad = cmg
                                    logger.add_scalar( "{}/SpeakerMaxGrad".format(mode), maxgrad, it_step)                    
                                    maxgrad = 0
                                    for name, p in listener.named_parameters() :
                                        if hasattr(p,'grad') and p.grad is not None:
                                            logger.add_histogram( "Listener/{}".format(name), p.grad, it_step)                    
                                            cmg = torch.abs(p.grad).max()
                                            if cmg > maxgrad:
                                                maxgrad = cmg
                                    logger.add_scalar( "{}/ListenerMaxGrad".format(mode), maxgrad, it_step)                    
                                
                                if self.config['with_utterance_penalization'] or self.config['with_utterance_promotion']:
                                    for widx in range(self.config['vocab_size']+1):
                                        logger.add_scalar("{}/Word{}Counts".format(mode,widx), speaker_outputs['speaker_utterances_count'][widx], it_step)
                                    logger.add_scalar("{}/OOVLoss".format(mode), speaker_losses['oov_loss'][idx_loss].mean().item(), it_step)

                                if 'with_mdl_principle' in self.config and self.config['with_mdl_principle']:
                                    logger.add_scalar("{}/MDLLoss".format(mode), speaker_losses['mdl_loss'][idx_loss].mean().item(), it_step)
                                
                                #sentence_length = sum([ float(s.size(1)) for s in speaker_outputs['sentences_widx']])/len(speaker_outputs['sentences_widx'])
                                sentence_length = (speaker_outputs['sentences_widx']< (self.config['vocab_size']-1)).sum().float()/batch_size
                                logger.add_scalar('{}/SentenceLength (/{})'.format(mode, self.config['max_sentence_length']), sentence_length/self.config['max_sentence_length'], it_step)
                                
                                for sentence in sentences:  total_sentences.append(sentence.replace(chr(97+self.config['vocab_size']), ''))
                                total_nbr_unique_sentences = cardinality(total_sentences)
                                total_nbr_unique_stimulus += batch_size
                                logger.add_scalar('{}/Ambiguity (%)'.format(mode), float(total_nbr_unique_stimulus-total_nbr_unique_sentences)/total_nbr_unique_stimulus*100.0, it_step)
                                
                                entropies_per_sentence = torch.cat([torch.cat([ torch.distributions.categorical.Categorical(logits=w_logits).entropy().view(1,1) for w_logits in s_logits], dim=-1).mean(dim=-1) for s_logits in speaker_outputs['sentences_logits']], dim=0)
                                # (batch_size, )
                                logger.add_scalar('{}/Entropy'.format(mode), entropies_per_sentence.mean().item(), it_step)
                                
                                logger.add_scalar('{}/Loss'.format(mode), loss.item(), it_step)
                                
                                for l_name, l in losses.items():
                                    logger.add_scalar('{}/{}'.format(mode, l_name), l[idx_loss].item(), it_step)    

                                logger.add_scalar('{}/WeightMaxL1Loss'.format(mode), speaker_outputs['maxl1_loss'].item()+listener_outputs['maxl1_loss'].item(), it_step)
                                
                                decision_probs = listener_outputs['decision_probs']

                                if self.config['descriptive']:
                                    if 'obverter_least_effort_loss' in self.config and self.config['obverter_least_effort_loss']:
                                        for widx in range(len(losses4widx)):
                                            logger.add_scalar('{}/Loss@w{}'.format(mode,widx), losses4widx[widx].item(), it_step)
                                            acc = (torch.abs(decision_probs[:,widx,...]-target_decision_probs) < 0.5).float().mean()*100
                                            logger.add_scalar('{}/Accuracy@{}'.format(mode,widx), acc.item(), it_step)
                                    else:
                                        #acc = (torch.abs(decision_probs-target_decision_probs) < 0.5).float().mean()*100
                                        decision_idx = decision_probs.max(dim=-1)[1]
                                        acc = (decision_idx==sample['target_decision_idx']).float()#.mean()*100
                                else:
                                    decision_idx = decision_probs.max(dim=-1)[1]
                                    acc = (decision_idx==sample['target_decision_idx']).float()#.mean()*100
                                logger.add_scalar('{}/Accuracy'.format(mode), acc.mean().item()*100, it_step)
                                epoch_acc.append(acc.view(-1))
                                if end_of_epoch_sample:
                                    epoch_acc = torch.cat(epoch_acc, dim=0).mean()
                                    logger.add_scalar('{}/PerEpoch/Accuracy'.format(mode), epoch_acc.item()*100, epoch)
                                    epoch_acc = []
                                
                                #logger.add_histogram( "{}/LossesPerStimulus".format(mode), losses, it_step)
                                logger.add_scalar( "{}/Stimulus/Mean".format(mode), sample['listener_experiences'].mean(), it_step)
                                
                                if mode == 'train':
                                    if hasattr(speaker,'tau'): 
                                        #logger.add_histogram( "{}/Speaker/Tau".format(mode), speaker.tau, it_step)
                                        tau = torch.cat([ t.view((-1)) for t in speaker.tau], dim=0) if isinstance(speaker.tau, list) else speaker.tau
                                        logger.add_scalar( "{}/Tau/Speaker/Mean".format(mode), tau.mean().item(), it_step)
                                        logger.add_scalar( "{}/Tau/Speaker/Std".format(mode), tau.std().item(), it_step)
                                    if hasattr(listener,'tau'): 
                                        #logger.add_histogram( "{}/Listener/Tau".format(mode), listener.tau, it_step)
                                        tau = torch.cat([ t.view((-1)) for t in listener.tau], dim=0) if isinstance(listener.tau, list) else listener.tau
                                        logger.add_scalar( "{}/Tau/Listener/Mean".format(mode), tau.mean().item(), it_step)
                                        logger.add_scalar( "{}/Tau/Listener/Std".format(mode), tau.std().item(), it_step)

                            # //------------------------------------------------------------//
                            # //------------------------------------------------------------//
                            # //------------------------------------------------------------//
                            

                            if verbose_period is not None and idx_stimuli % verbose_period == 0:
                                #descr = 'Epoch {} :: {} Iteration {}/{} :: Loss {} = {}'.format(epoch, mode, idx_stimuli, len(data_loader), it_step, loss.item())
                                descr = 'Epoch {} :: {} Iteration {}/{} :: Loss {} = {}'.format(epoch, mode, idx_stimuli, len(data_loader), it, loss.item())
                                pbar.set_description_str(descr)
                                # Show some sentences:
                                if VERBOSE:
                                    for sidx in range(batch_size):
                                        if sidx>=10:
                                            break
                                        print(f"{sidx} : ", sentences[sidx], \
                                            f"\t /label: {sample['target_decision_idx'][sidx]}",\
                                            f" /decision: {decision_idx[sidx]}")

                            if self.config['use_curriculum_nbr_distractors']:
                                nbr_distractors = self.datasets[mode].getNbrDistractors()
                                logger.add_scalar( "{}/CurriculumNbrDistractors".format(mode), nbr_distractors, it_step)
                                logger.add_scalar( "{}/CurriculumWindowedAcc".format(mode), windowed_accuracy, it_step)
                            
                            
                            if hasattr(prototype_speaker,'VAE') and idx_stimuli % 4 == 0:
                                image_save_path = logger.path 
                                '''
                                '''
                                query_vae_latent_space(prototype_speaker.VAE, 
                                                       sample=sample['speaker_experiences'],
                                                       path=image_save_path,
                                                       test=('test' in mode),
                                                       full=('test' in mode),
                                                       idxoffset=it_rep+idx_stimuli*self.config['nbr_experience_repetition'],
                                                       suffix='speaker',
                                                       use_cuda=True)
                                query_vae_latent_space(prototype_listener.VAE, 
                                                       sample=sample['listener_experiences'],
                                                       path=image_save_path,
                                                       test=('test' in mode),
                                                       full=('test' in mode),
                                                       idxoffset=idx_stimuli,
                                                       suffix='listener')
                                
                        # //------------------------------------------------------------//
                        # //------------------------------------------------------------//
                        # //------------------------------------------------------------//

                        if self.config['use_cuda']:
                            speaker = speaker.cpu()
                            listener = listener.cpu()
                        
                        if mode == 'train' and self.config["cultural_pressure_it_period"] is not None and (idx_stimuli+len(data_loader)*epoch) % self.config['cultural_pressure_it_period'] == 0:
                            if 'oldest' in self.config['cultural_reset_strategy']:
                                if 'S' in self.config['cultural_reset_strategy']:
                                    weights = [ it-agents_stats[agent.agent_id]['reset_iterations'][-1] for agent in speakers ] 
                                    idx_speaker2reset = random.choices( range(len(speakers)), weights=weights)[0]
                                elif 'L' in self.config['cultural_reset_strategy']:
                                    weights = [ it-agents_stats[agent.agent_id]['reset_iterations'][-1] for agent in listeners ] 
                                    idx_listener2reset = random.choices( range(len(listeners)), weights=weights)[0]
                                else:
                                    weights = [ it-agents_stats[agent.agent_id]['reset_iterations'][-1] for agent in listeners ] 
                                    weights += [ it-agents_stats[agent.agent_id]['reset_iterations'][-1] for agent in speakers ]
                                    idx_agent2reset = random.choices( range(len(listeners)+len(speakers)), weights=weights)[0]
                            else: #uniform
                                if 'S' in self.config['cultural_reset_strategy']:
                                    idx_speaker2reset = random.randint(0,len(speakers)-1)
                                elif 'L' in self.config['cultural_reset_strategy']:
                                    idx_listener2reset = random.randint(0,len(listeners)-1)
                                else:
                                    idx_agent2reset = random.randint(0,2*len(listeners)-1)

                            if 'S' in self.config['cultural_reset_strategy']:
                                if 'meta' in self.config['cultural_reset_strategy']:
                                    self._apply_meta_update(meta_learner=meta_agents[type(speakers[idx_speaker2reset])],
                                                           meta_optimizer=meta_agents_optimizers[type(speakers[idx_speaker2reset])],
                                                           learner=speakers[idx_speaker2reset])
                                else:
                                    speakers[idx_speaker2reset].reset()
                                speakers_optimizers[idx_speaker2reset] = optim.Adam(speakers[idx_speaker2reset].parameters(), lr=self.config['learning_rate'], eps=self.config['adam_eps'])
                                agents_stats[speakers[idx_speaker2reset].agent_id]['reset_iterations'].append(it)
                                print("Agent Speaker {} has just been resetted.".format(speakers[idx_speaker2reset].agent_id))
                            
                            if 'L' in self.config['cultural_reset_strategy']:
                                if 'meta' in self.config['cultural_reset_strategy']:
                                    self._apply_meta_update(meta_learner=meta_agents[type(listeners[idx_listener2reset])],
                                                           meta_optimizer=meta_agents_optimizers[type(listeners[idx_listener2reset])],
                                                           learner=listeners[idx_listener2reset])
                                else:
                                    listeners[idx_listener2reset].reset()
                                listeners_optimizers[idx_listener2reset] = optim.Adam(listeners[idx_listener2reset].parameters(), lr=self.config['learning_rate'], eps=self.config['adam_eps'])
                                agents_stats[listeners[idx_listener2reset].agent_id]['reset_iterations'].append(it)
                                print("Agent  Listener {} has just been resetted.".format(speakers[idx_listener2reset].agent_id))

                            if 'L' not in self.config['cultural_reset_strategy'] and 'S' not in self.config['cultural_reset_strategy']:
                                if idx_agent2reset < len(listeners):
                                    agents = listeners 
                                    agents_optimizers = listeners_optimizers
                                else:
                                    agents = speakers 
                                    agents_optimizers = speakers_optimizers
                                    idx_agent2reset -= len(listeners)
                                if 'meta' in self.config['cultural_reset_strategy']:
                                    self._apply_meta_update(meta_learner=meta_agents[type(agents[idx_agent2reset])],
                                                           meta_optimizer=meta_agents_optimizers[type(agents[idx_agent2reset])],
                                                           learner=agents[idx_agent2reset])
                                else:
                                    agents[idx_agent2reset].reset()
                                    agents_optimizers[idx_agent2reset] = optim.Adam(agents[idx_agent2reset].parameters(), lr=self.config['learning_rate'], eps=self.config['adam_eps'])
                                    agents_stats[agents[idx_agent2reset].agent_id]['reset_iterations'].append(it)
                                print("Agents {} has just been resetted.".format(agents[idx_agent2reset].agent_id))
                        
                        if self.config['use_curriculum_nbr_distractors'] and mode == 'train':
                            nbr_distractors = self.datasets['train'].getNbrDistractors()
                            windowed_accuracy = (windowed_accuracy*window_count+acc.item())
                            window_count += 1
                            windowed_accuracy /= window_count
                            if windowed_accuracy > 60 and window_count > self.config['curriculum_distractors_window_size'] and nbr_distractors < self.config['nbr_distractors'] :
                                windowed_accuracy = 0
                                window_count = 0
                                self.datasets['train'].setNbrDistractors(self.datasets['train'].getNbrDistractors()+1)
                                self.datasets['test'].setNbrDistractors(self.datasets['test'].getNbrDistractors()+1)
                        # //------------------------------------------------------------//
                                            
                if logger is not None:
                    if mode == 'test':  
                        max_nbr_samples = None
                    else:   
                        max_nbr_samples = int(len(total_sentences)*0.1)

                    topo_sims, pvalues, unique_prod_ratios = logger.measure_topographic_similarity(sentences_key='sentences_widx',
                                                                               features_key='latent_experiences',
                                                                               max_nbr_samples=max_nbr_samples,
                                                                               verbose=VERBOSE,
                                                                               max_workers=self.config['parallel_TS_computation_max_workers'])
                    topo_sims_v, pvalues_v, unique_prod_ratios_v = logger.measure_topographic_similarity(sentences_key='sentences_widx',
                                                                               features_key='latent_experiences_values',
                                                                               max_nbr_samples=max_nbr_samples,
                                                                               verbose=VERBOSE,
                                                                               max_workers=self.config['parallel_TS_computation_max_workers'])
                    feat_topo_sims, feat_pvalues, _ = logger.measure_topographic_similarity(sentences_key='sentences_widx',
                                                                               features_key='temporal_features',
                                                                               max_nbr_samples=max_nbr_samples,
                                                                               verbose=VERBOSE,
                                                                               max_workers=self.config['parallel_TS_computation_max_workers'])
                    
                    for agent_id in topo_sims:
                        logger.add_scalar('{}/{}/TopographicSimilarity'.format(mode,agent_id), topo_sims[agent_id], epoch)
                        logger.add_scalar('{}/{}/TopographicSimilarity-UniqueProduction'.format(mode,agent_id), unique_prod_ratios[agent_id], epoch)
                        logger.add_scalar('{}/{}/TopographicSimilarity-PValues'.format(mode,agent_id), pvalues[agent_id], epoch)
                    for agent_id in topo_sims_v:
                        logger.add_scalar('{}/{}/TopographicSimilarity_withValues'.format(mode,agent_id), topo_sims_v[agent_id], epoch)
                        logger.add_scalar('{}/{}/TopographicSimilarity_withValues-PValues'.format(mode,agent_id), pvalues_v[agent_id], epoch)
                    for agent_id in feat_topo_sims:
                        logger.add_scalar('{}/{}/FeaturesTopographicSimilarity (%)'.format(mode,agent_id), feat_topo_sims[agent_id], epoch)
                    
                    logger.switch_epoch()

            # Save agent:
            for agent in speakers:
                agent.save(path=os.path.join(self.config['save_path'],'{}_{}.pt'.format(agent.kwargs['architecture'], agent.agent_id)))
            for agent in listeners:
                agent.save(path=os.path.join(self.config['save_path'],'{}_{}.pt'.format(agent.kwargs['architecture'], agent.agent_id)))
            
            if 'meta' in self.config['cultural_reset_strategy']:
                for agent in meta_agents.values():
                    agent.save(path=os.path.join(self.config['save_path'],'{}_{}.pt'.format(agent.kwargs['architecture'], agent.agent_id)))
            
    def _reptile_step(self, learner, reptile_learner, nbr_grad_steps=1, verbose=False) :
        k = 1.0/float(nbr_grad_steps)
        nbrParams = 0
        nbrUpdatedParams = 0
        for (name, lp), (namer, lrp) in zip( learner.named_parameters(), reptile_learner.named_parameters() ) :
            nbrParams += 1
            if lrp.grad is not None:
                nbrUpdatedParams += 1
                lrp.grad.data.copy_( k*(lp.data-lrp.data) )
            else:
                lrp.grad = k*(lp.data-lrp.data)
                if verbose:
                    print("Parameter {} has not been updated...".format(name))
        print("Meta-cultural learning step :: {}/{} updated params.".format(nbrUpdatedParams, nbrParams))
        return 

    def _apply_meta_update(self, meta_learner, meta_optimizer, learner):
        meta_learner.zero_grad()
        self._reptile_step(learner=learner, reptile_learner=meta_learner)
        meta_optimizer.step()
        learner.load_state_dict( meta_learner.state_dict())
        return 




            




