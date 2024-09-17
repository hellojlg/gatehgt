import importlib

from torch.utils.data import Dataset, DataLoader
import torch
from torch_geometric.utils import to_networkx
from transformers import AutoTokenizer, AutoModel
from torch_geometric.data import HeteroData
from typing import Dict, List, Union
import torch
import torch.nn.functional as F
from torch import nn
import torch_geometric.transforms as T
from torch_geometric.nn import Linear
from torch_geometric.data import HeteroData
import json
import random
def run_model(submodel_name):
    try:

        submodule = importlib.import_module(submodel_name)
        globals().update(vars(submodule))
        print(f"{submodel_name}.")
    except ModuleNotFoundError:
        raise ValueError(f"'{submodel_name}' not found")

class HGT(nn.Module):
    def __init__(
        self,
        device,
        in_channels: Union[int, Dict[str, int]],
        hidden_channels,
        out_channels: int,
        metadata,
        heads=4,
        rnn_type='gru'
    ):
        super().__init__()
        self.device = device
        self.bert_model = AutoModel.from_pretrained("../microsoft/codebert-base")
        self.hgt_conv = HGTConv(in_channels, hidden_channels, metadata, heads,rnn_type=rnn_type)
        self.hgt_conv1 = HGTConv(hidden_channels, hidden_channels, metadata, heads,rnn_type=rnn_type)
        self.lin = Linear(hidden_channels, out_channels)
        self.ln = nn.LayerNorm(out_channels)
        self.relu = nn.ReLU()
        self.ln.reset_parameters()

    def forward(self, pyg, delIndexes):
        token_ids_dict = pyg.token_ids_dict
        if token_ids_dict["add_node"].numel() != 0:
            pyg["add_node"].x = self.bert_model(
                torch.tensor(
                    token_ids_dict["add_node"].tolist(),
                    dtype=torch.long,
                    device=self.device,
                )
            )[0][:, 0, :]
        if token_ids_dict["del_node"].numel() != 0:
            pyg["del_node"].x = self.bert_model(
                torch.tensor(
                    token_ids_dict["del_node"].tolist(),
                    dtype=torch.long,
                    device=self.device,
                )
            )[0][:, 0, :]
        if token_ids_dict["add_node"].numel() == 0:
            pyg["add_node"].x = torch.zeros(
                (0, 768), dtype=torch.float, device=self.device
            )
        if token_ids_dict["del_node"].numel() == 0:
            pyg["del_node"].x = torch.zeros(
                (0, 768), dtype=torch.float, device=self.device
            )
        out0 = self.hgt_conv(pyg.x_dict, pyg.edge_index_dict)
        out0 = self.hgt_conv1(out0, pyg.edge_index_dict)
        return torch.index_select(self.relu(self.ln(self.lin(out0["del_node"]))), 0, delIndexes)

    def predict(self, pyg, delIndexes):
        token_ids_dict = pyg.token_ids_dict
        if token_ids_dict["add_node"].numel() != 0:
            pyg["add_node"].x = self.bert_model(
                torch.tensor(
                    token_ids_dict["add_node"].tolist(),
                    dtype=torch.long,
                    device=self.device,
                )
            )[0][:, 0, :]
        if token_ids_dict["del_node"].numel() != 0:
            pyg["del_node"].x = self.bert_model(
                torch.tensor(
                    token_ids_dict["del_node"].tolist(),
                    dtype=torch.long,
                    device=self.device,
                )
            )[0][:, 0, :]
        if token_ids_dict["add_node"].numel() == 0:
            pyg["add_node"].x = torch.zeros(
                (0, 768), dtype=torch.float, device=self.device
            )
        if token_ids_dict["del_node"].numel() == 0:
            pyg["del_node"].x = torch.zeros(
                (0, 768), dtype=torch.float, device=self.device
            )
        out0 = self.hgt_conv(pyg.x_dict, pyg.edge_index_dict)
        out0 = self.hgt_conv1(out0, pyg.edge_index_dict)
        return torch.index_select(self.relu(self.ln(self.lin(out0["del_node"]))), 0, delIndexes)


class rankNet(nn.Module):
    def __init__(self, num_features):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(num_features, 32),
            nn.Linear(32, 16),
            nn.Linear(16, 8),
            nn.Linear(8, 1),
        )

        self.output = nn.Sigmoid()

    def forward(self, input1, input2):
        s1 = self.model(input1)
        s2 = self.model(input2)
        return self.output(s1 - s2)

    def predict(self, input):
        return self.model(input)