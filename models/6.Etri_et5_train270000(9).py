# -*- coding: utf-8 -*-
"""Etri_et5_train_epochs1추가_270000(9)

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/17HKabpt-YFwPQCzgggWbjES1DJBpJ9u3

참고 url : https://github.com/abhimishra91/transformers-tutorials/blob/master/transformers_summarization_wandb.ipynb
"""

!pip install transformers
!pip install sentencepiece==0.1.91

"""transformers version = '4.12.5'"""

from google.colab import drive
drive.mount('/content/drive')

# model.generate(pieces)
from transformers import T5Config, T5Tokenizer, T5ForConditionalGeneration
from tqdm import tqdm
import torch
from torch.utils.data import DataLoader

model_folder = '/content/drive/MyDrive/3차프로젝트_현정/eT5_epoch8/pretrained_270000'

model = T5ForConditionalGeneration.from_pretrained(model_folder)
tokenizer = T5Tokenizer.from_pretrained(model_folder)

device = 'cuda' if torch.cuda.is_available() else 'cpu'

class CustomDataset:

    def __init__(self, dataframe, tokenizer, source_len, summ_len):
        self.tokenizer = tokenizer
        self.data = dataframe
        self.source_len = source_len
        self.summ_len = summ_len
        self.text = self.data.text
        self.ctext = self.data.ctext

    def __len__(self):
        return len(self.text)

    def __getitem__(self, index):
        ctext = str(self.ctext[index])
        ctext = ' '.join(ctext.split())

        text = str(self.text[index])
        text = ' '.join(text.split())

        source = self.tokenizer.batch_encode_plus([ctext], max_length= self.source_len, pad_to_max_length=True,return_tensors='pt')
        target = self.tokenizer.batch_encode_plus([text], max_length= self.summ_len, pad_to_max_length=True,return_tensors='pt')

        source_ids = source['input_ids'].squeeze()
        source_mask = source['attention_mask'].squeeze()
        target_ids = target['input_ids'].squeeze()
        target_mask = target['attention_mask'].squeeze()

        return {
            'source_ids': source_ids.to(dtype=torch.long), 
            'source_mask': source_mask.to(dtype=torch.long), 
            'target_ids': target_ids.to(dtype=torch.long),
            'target_ids_y': target_ids.to(dtype=torch.long)
        }

def train(epoch, tokenizer, model, device, loader, optimizer):
    model.train()
    for _,data in tqdm(enumerate(loader, 0)):
        y = data['target_ids'].to(device, dtype = torch.long)
        y_ids = y[:, :-1].contiguous()
        lm_labels = y[:, 1:].clone().detach()
        lm_labels[y[:, 1:] == tokenizer.pad_token_id] = -100
        ids = data['source_ids'].to(device, dtype = torch.long)
        mask = data['source_mask'].to(device, dtype = torch.long)

        outputs = model(input_ids = ids, attention_mask = mask, decoder_input_ids=y_ids, labels=lm_labels)
        loss = outputs[0]
        
        if _%10 == 0:
            pass
            
        if _%500==0:
            print(f'Epoch: {epoch}, Loss:  {loss.item()}')
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        # xm.optimizer_step(optimizer)
        # xm.mark_step()

def validate(epoch, tokenizer, model, device, loader):
    model.eval()
    predictions = []
    actuals = []
    with torch.no_grad():
        for _, data in enumerate(loader, 0):
            y = data['target_ids'].to(device, dtype = torch.long)
            ids = data['source_ids'].to(device, dtype = torch.long)
            mask = data['source_mask'].to(device, dtype = torch.long)

            generated_ids = model.generate(
                input_ids = ids,
                attention_mask = mask, 
                max_length=150, 
                num_beams=2,
                repetition_penalty=2.5, 
                length_penalty=1.0, 
                early_stopping=True
                )
            preds = [tokenizer.decode(g, skip_special_tokens=True, clean_up_tokenization_spaces=True) for g in generated_ids]
            target = [tokenizer.decode(t, skip_special_tokens=True, clean_up_tokenization_spaces=True)for t in y]
            if _%100==0:
                print(f'Completed {_}')

            predictions.extend(preds)
            actuals.extend(target)
    return predictions, actuals

model.to(device)

"""hyper-parameters"""

config = T5Config()
config.MAX_LEN = 1024
config.SUMMARY_LEN = 150 
config.TRAIN_BATCH_SIZE = 2       # input batch size for training (default: 64)
config.VALID_BATCH_SIZE = 2    # input batch size for testing (default: 1000)
config.TRAIN_EPOCHS = 1       # number of epochs to train (default: 10)
config.VAL_EPOCHS = 1
config.LEARNING_RATE = 1e-4    # learning rate (default: 0.01)
config.SEED = 42               # random seed (default: 42)

train_params = {
        'batch_size': config.TRAIN_BATCH_SIZE,
        'shuffle': True,
        'num_workers': 0
        }

val_params = {
        'batch_size': config.VALID_BATCH_SIZE,
        'shuffle': False,
        'num_workers': 0
        }

optimizer = torch.optim.Adam(params =  model.parameters(), lr=config.LEARNING_RATE)

"""dataset"""

import pandas as pd
train_dataset1 = pd.read_csv('/content/drive/MyDrive/3차 프로젝트/dataset/train.csv')[['document','label']].iloc[:240000]
train_dataset2 = pd.read_csv('/content/drive/MyDrive/3차 프로젝트/dataset/extract_data/validation_data.csv')[['document','label']].iloc[:30000]
train_dataset = pd.concat([train_dataset1,train_dataset2]) # 270000개
validation_dataset = pd.read_csv('/content/drive/MyDrive/3차 프로젝트/dataset/valid.csv')[['document','label']].iloc[:500]

import numpy as np
train_dataset.set_index(np.arange(0,270000),inplace=True)

"""train"""

train_dataset.columns = ['ctext','text']
train_dataset.ctext = 'summarize: ' + train_dataset.ctext

training_set = CustomDataset(train_dataset, tokenizer, config.MAX_LEN, config.SUMMARY_LEN)
training_loader = DataLoader(training_set, **train_params)

for epoch in range(config.TRAIN_EPOCHS):
    print (1)
    train(epoch, tokenizer, model, device, training_loader, optimizer)
    tokenizer.save_pretrained('/content/drive/MyDrive/3차프로젝트_현정/eT5_epoch8/pretrained_270000(9)/{}'.format(epoch))
    model.save_pretrained('/content/drive/MyDrive/3차프로젝트_현정/eT5_epoch8/pretrained_270000(9)/{}'.format(epoch))

tokenizer.save_pretrained('/content/drive/MyDrive/3차프로젝트_현정/eT5_epoch8/pretrained_270000(9)/')
model.save_pretrained('/content/drive/MyDrive/3차프로젝트_현정/eT5_epoch8/pretrained_270000(9)/')

"""test"""

validation_dataset.columns = ['ctext','text']
validation_dataset.ctext = 'summarize: ' + validation_dataset.ctext

val_set = CustomDataset(validation_dataset, tokenizer, config.MAX_LEN, config.SUMMARY_LEN)

val_loader = DataLoader(val_set, **val_params)

for epoch in range(config.VAL_EPOCHS):
    predictions, actuals = validate(epoch, tokenizer, model, device, val_loader)
    final_df = pd.DataFrame({'Generated Text':predictions,'Actual Text':actuals})

final_df.to_csv('/content/drive/MyDrive/3차프로젝트_현정/eT5_epoch8/final_df_train270000(9).csv')

