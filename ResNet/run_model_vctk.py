from torchsummary import summary
import os
import glob
import torch
import librosa
import pickle
import copy
import random

import numpy as np
import pandas as pd
import scipy.signal as signal

import torch.optim as optim
import torch.nn as nn
import torch.nn.functional as F

from model import Net_ResNet50

from torch.utils.data import random_split, Dataset, DataLoader
from tqdm import tqdm

# Parameters
dataset_dir = '/home/bbekci/inzpeech/preprocessed_vctk.pkl'
max_epochs = 10
batch_size = 256

# CUDA for PyTorch
use_cuda = torch.cuda.is_available()
device = torch.device('cuda:0' if use_cuda else 'cpu')
torch.backends.cudnn.benchmark = True


def test_val_calculations(data_set_loader, _n_classes, _net):
    class_correct = [0] * _n_classes
    class_total = [0] * _n_classes
    with torch.no_grad():
        for data in data_set_loader:
            inputs = data[0].to(device, dtype=torch.float)
            labels = data[1].to(device)
            outputs = _net(inputs)
            _, predicted = torch.max(outputs, 1)
            c = (predicted == labels)
            for i in range(len(labels)):
                label = labels[i]
                class_correct[label] += c[i].item()
                class_total[label] += 1

    mean_acc = 0
    div_count = 0
    for i in range(_n_classes):
       
        if class_total[i] != 0:
            mean_acc += (100 * class_correct[i] / class_total[i])
            div_count += 1

    return mean_acc / div_count


class PreprocessedDataset(Dataset):
    def __init__(self, file_dir):
        self.file_dir = file_dir
        self.lst = None
        
        with open(file_dir, 'rb') as pickle_load:
            self.lst = pickle.load(pickle_load)

        random.shuffle(self.lst)

    def __len__(self):
        return len(self.lst)

    def n_class(self):
        return np.max(np.array([i[0] for i in self.lst])) + 1

    def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()

        sound_data = self.lst[idx][1]
        label = self.lst[idx][0]
        sound_data = np.expand_dims(sound_data, axis=0)
        sample = (sound_data, label)

        return sample


sound_data = PreprocessedDataset(file_dir=dataset_dir)
len_sound_data = len(sound_data)

n_classes = sound_data.n_class()

train_data_count = int(len_sound_data * 0.8)
val_data_count = int(len_sound_data * 0.1)
test_data_count = len_sound_data - val_data_count - train_data_count
train_data, val_data, test_data = random_split(sound_data,
                                               [train_data_count,
                                                val_data_count,
                                                test_data_count]
                                               )

train_dataset_loader = torch.utils.data.DataLoader(train_data,
                                                   batch_size=batch_size,
                                                   shuffle=True,
                                                   num_workers=16)

val_dataset_loader = torch.utils.data.DataLoader(val_data,
                                                 batch_size=batch_size,
                                                 shuffle=True,
                                                 num_workers=16)

test_dataset_loader = torch.utils.data.DataLoader(test_data,
                                                  batch_size=batch_size,
                                                  shuffle=True,
                                                  num_workers=16)

print('Test Data Size: %s' % len(test_dataset_loader.dataset))
print('Val Data Size: %s' % len(val_dataset_loader.dataset))
print('Train Data Size: %s' % len(train_dataset_loader.dataset))


net = Net_ResNet50(img_channel=1, num_classes=n_classes)
net.to(device)
# net.load_state_dict(torch.load('/home/bbekci/inzpeech/ResNet/model/mode.pth'))

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(net.parameters(), lr=1e-4)

for epoch in range(max_epochs):  # loop over the dataset multiple times
    correct_pred = 0
    for i, data in enumerate(train_dataset_loader):
        # get the inputs; data is a list of [inputs, labels]
        inputs = data[0].to(device, dtype=torch.float)
        labels = data[1].to(device)

        # zero the parameter gradients
        optimizer.zero_grad()

        # forward + backward + optimize
        output = net(inputs)
        loss = criterion(output, labels)
        loss.backward()
        optimizer.step()

        _, predicted = torch.max(output.data, 1)
        correct_pred += (predicted == labels).float().sum()
        print('[%d, %5d] loss: %.3f' % (epoch + 1, i + 1, loss))

    # Validation
    val_acc = test_val_calculations(val_dataset_loader, n_classes, net)
    print('Val Acc: %.6f' % val_acc)

    # Calculate Train Accuracy
    train_acc = 100 * correct_pred / len(train_data)
    print('Train Acc: %.6f' % train_acc)


# torch.save(best_net.state_dict(), '/home/bbekci/inzpeech/ResNet/model/model.pth')
test_acc = test_val_calculations(test_dataset_loader, n_classes, net)
print('Test Acc: %.6f' % test_acc)


