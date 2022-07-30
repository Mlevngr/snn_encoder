import torch
import torch.nn as nn
import torch.nn.functional as F
import snntorch.surrogate as surrogate
import snntorch as snn
import numpy as np
from utils.config import INITIAL_MEAN_DICT
from utils.monitor import Monitor

class TextCNN(nn.Module):
    def __init__(self, args, spike_grad=surrogate.fast_sigmoid(slope=25)) -> None:
        super().__init__()
        self.initial_method = "kaiming_uniform"
        self.positive_init_rate = 0.8
        self.convs_1 = nn.ModuleList([
            nn.Conv2d(in_channels=1, out_channels=args.filter_num, kernel_size=(filter_size, args.hidden_dim))
            for filter_size in args.filters
        ])
        self.maxpool_1 = nn.ModuleList([
            nn.MaxPool2d((args.sentence_length - filter_size + 1, 1)) for filter_size in args.filters
        ])
        self.lif1 = snn.Leaky(beta=args.beta, spike_grad=spike_grad, init_hidden=True, threshold=1.0)
        self.fc_1 = nn.Linear(len(args.filters)*args.filter_num, args.label_num)
        self.lif2 = snn.Leaky(beta=args.beta, spike_grad=spike_grad, init_hidden=True, threshold=1.0, output=True)
        self.dead_neuron_checker = args.dead_neuron_checker
        self.initial_method = args.initial_method
        self.positive_init_rate = args.positive_init_rate
    
    def initial(self):
        for c in self.convs_1:
            c.weight.data.add_(INITIAL_MEAN_DICT['conv-kaiming'][self.positive_init_rate])
        m = self.fc_1
        m.weight.data.add_(INITIAL_MEAN_DICT["linear-kaiming"][self.positive_init_rate])

        # if self.initial_method == 'kaiming' or self.initial_method == 'k+x':
        #     for c in self.convs_1:
        #         # torch.nn.init.kaiming_normal_(c.weight.data)
        #         c.weight.data.add_(INITIAL_MEAN_DICT['kaiming'][self.positive_init_rate])

        # if self.initial_method != 'zero':
        #     for m in self.modules():
        #         if isinstance(m, nn.Linear):
        #             if self.initial_method == 'normal' or 'k+n':
        #                 nn.init.normal_(m.weight.data, mean=INITIAL_MEAN_DICT['normal'][self.positive_init_rate], std=0.01)
        #             elif self.initial_method == 'xavier' or self.initial_method == 'k+x':
        #                 nn.init.xavier_normal_(m.weight.data)
        #                 m.weight.data.add_(INITIAL_MEAN_DICT['xavier'][self.positive_init_rate])

    def forward(self, x):
        batch_size = x.shape[0]
        x = x.unsqueeze(dim=1)
        conv_out = [conv(x) for conv in self.convs_1]
        pooled_out = [self.maxpool_1[i](conv_out[i]) for i in range(len(self.maxpool_1))]
        spks = [self.lif1(pooled) for pooled in pooled_out]
        spks_1 = torch.cat(spks, dim=1).view(batch_size, -1)
        cur2 = self.fc_1(spks_1)
        spk2, mem2 = self.lif2(cur2)
        if self.dead_neuron_checker == "True":
            temp_spks = spks_1.sum(dim=0)
            Monitor.add_monitor(temp_spks, 0)
        return spks_1, spk2, mem2
        
