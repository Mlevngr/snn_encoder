import sys
sys.path.append("..")
import re
import numpy as np
import pickle
import torch
from tqdm import tqdm
import os
from dataset import TensorDataset


def clean_tokenize(data, lower=False):
    # recover some abbreviations
    data = re.sub(r"\-", " ", data)
    data = re.sub(r"\/", " ", data)
    data = re.sub(r"\s{2,}", " ", data)
    data = data.lower() if lower else data

    # split all tokens, form a list
    return [x.strip() for x in data.split() if x.strip()]

class TensorEncoder():
    def __init__(self, vocab_path, dataset_name, datafile_path, sent_length:int, embedding_dim:int, data_type="trian", bias=3) -> None:
        super(TensorEncoder, self).__init__()
        self.vocab_path = vocab_path
        self.dataset_name = dataset_name
        self.datafile_path = datafile_path
        self.sent_length = sent_length
        self.embedding_dim = embedding_dim
        self.data_type = data_type
        self.bias = bias

    def encode(self):
        glove_dict = {}
        with open(self.vocab_path, "r") as f:
            for line in f:
                values = line.split()
                word = values[0]
                vector = np.asarray(values[1:], "float32")
                glove_dict[word] = vector

        mean_embedding = np.mean(np.array(list(glove_dict.values())), axis=0)
        zero_embedding = np.array([0] * self.embedding_dim, dtype=float)
        mean_value = np.mean(list(glove_dict.values()))
        variance_value = np.var(list(glove_dict.values()))
        left_boundary = mean_value - self.bias * np.sqrt(variance_value)
        right_boundary = mean_value + self.bias * np.sqrt(variance_value)

        sample_list = []
        with open(self.datafile_path, "r") as f:
            for line in f.readlines():
                temp = line.split('\t')
                sentence = temp[0].strip()
                label = int(temp[1])
                sample_list.append((sentence, label))

        embedding_tuple_list = []
        for i in tqdm(range(len(sample_list))):
            sent_embedding = np.array([[0] * self.embedding_dim] * self.sent_length, dtype=float)
            text_list = clean_tokenize(sample_list[i][0])
            label = sample_list[i][1]
            for j in range(self.sent_length):
                if j >= len(text_list):
                    embedding_norm = zero_embedding # zero padding
                else:
                    word = text_list[j]
                    embedding = glove_dict[word] if word in glove_dict.keys() else zero_embedding
                    # N(0, 1)
                    embedding_n01 = (embedding - np.array([mean_value] * self.embedding_dim)) / np.array([np.sqrt(variance_value)] * self.embedding_dim)
                    embedding_norm = np.array([0] * self.embedding_dim, dtype=float)
                    for k in range(self.embedding_dim):
                        if embedding[k] < left_boundary:
                            embedding_norm[k] = -self.bias
                        elif embedding[k] > right_boundary:
                            embedding_norm[k] = self.bias
                        else:
                            embedding_norm[k] = embedding_n01[k]
                    # add abs(left_embedding)
                    embedding_norm = (embedding_norm + np.array([np.abs(self.bias)] * self.embedding_dim))/(self.bias * 2)
                    # embedding_norm = np.clip(embedding_norm, a_min=0, a_max=1)
                sent_embedding[j] = embedding_norm
            # print(i, sent_embedding)
            embedding_tuple_list.append((torch.tensor(sent_embedding), label))
        
        dataset = TensorDataset(embedding_tuple_list)

        file_name = f"../data/sst2/new_{self.data_type}_u_{self.bias}v_{self.dataset_name}_glove{self.embedding_dim}d_sent_len{self.sent_length}.tensor_dataset"
        if not os.path.exists(file_name):
            with open(file_name, 'wb') as f:
                pickle.dump(dataset, f, -1)
                
        return dataset


if __name__ == "__main__":
    tensor_encoder = TensorEncoder(
        vocab_path="../data/glove.6B.100d.txt",
        data_type="test",
        datafile_path="../data/sst2/test.txt", 
        dataset_name="sst2",
        sent_length=20,
        embedding_dim=100,
        bias = 3
    )
    tensor_encoder.encode()