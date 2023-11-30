import time
import random
import matplotlib.pyplot as plt
import numpy as np
import torch
import logging
import pickle
from sklearn.metrics import precision_score, recall_score, f1_score
import torch.nn.functional as F
from torch_geometric.nn import GCNConv
from torch_geometric.loader import DataLoader

class GCN(torch.nn.Module):
    def __init__(self, layer_sizes):
        super(GCN, self).__init__()
        self.layers = torch.nn.ModuleList()

        for i in range(len(layer_sizes) - 1):
            self.layers.append(GCNConv(layer_sizes[i], layer_sizes[i+1]))

    def forward(self, data):
        x, edge_index = data.x, data.edge_index

        for i, layer in enumerate(self.layers):
            x = layer(x, edge_index)
            if i < len(self.layers) - 1:  # Apply ReLU and Dropout to all but the last layer
                x = F.relu(x)
                x = F.dropout(x, training=self.training)
        
        # return F.log_softmax(x, dim=1)
        return x

def split_snapshots(snapshot_sequence, train_share=0.8, val_share=0.2):
    """
    Split the snapshots into training and validation sets.
    """
    n_snapshots = len(snapshot_sequence)
    n_train = int(train_share * n_snapshots)
    n_val = int(val_share * n_snapshots)

    # Ensure that we have at least one snapshot in each set
    n_train = max(1, n_train)
    n_val = max(1, n_val)

    # Shuffle and split the snapshot indices
    indices = list(range(n_snapshots))
    random.shuffle(indices)
    train_indices = indices[:n_train]
    val_indices = indices[n_train:n_train + n_val]

    train_snapshots = [snapshot_sequence[i] for i in train_indices]
    val_snapshots = [snapshot_sequence[i] for i in val_indices]

    return train_snapshots, val_snapshots


def evaluate_model(model, data_loader):
    model.eval()
    total_loss = 0
    all_predicted_labels = []
    all_true_labels = []
    with torch.no_grad():
        for batch in data_loader:
            out = model(batch)
            loss = F.nll_loss(out, batch.y)
            total_loss += loss.item()
            predicted_labels = out.max(1)[1]
            all_predicted_labels.append(predicted_labels.cpu().numpy())
            true_labels = batch.y
            all_true_labels.append(true_labels.cpu().numpy())

    all_predicted_labels = np.concatenate(all_predicted_labels)
    all_true_labels = np.concatenate(all_true_labels)

    return total_loss / len(data_loader), all_predicted_labels, all_true_labels

def plot_training_results(filename, loss_values, val_loss_values):
    plt.figure(figsize=(10, 6))
    plt.plot(loss_values, label='Training Loss')
    plt.plot(val_loss_values, label='Validation Loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.title('Training and Validation Loss Curve')
    plt.legend()
    plt.savefig('loss_curves/' + filename)
    plt.close()

def print_results(methods, snapshot_sequence, test_true_labels, test_predicted_labels, start_time):
    true_positives = np.sum(np.logical_and(test_predicted_labels == 1, test_true_labels == 1))
    false_positives = np.sum(np.logical_and(test_predicted_labels == 1, test_true_labels == 0))
    false_negatives = np.sum(np.logical_and(test_predicted_labels == 0, test_true_labels == 1))
    true_negatives = np.sum(np.logical_and(test_predicted_labels == 0, test_true_labels == 0))
    logging.info(f'{methods} training completed. Time: {time.time() - start_time:.2f}s.')
    logging.debug(f'Test: Predicted Labels: \n{test_predicted_labels}')
    logging.debug(f'Test: True Labels: \n{test_true_labels}') 
    logging.info(f'{methods}. Test: True Positives: {true_positives}, False Positives: {false_positives}, False Negatives: {false_negatives}, True Negatives: {true_negatives}.')
    precision = precision_score(test_true_labels, test_predicted_labels, average='binary', zero_division=0)
    recall = recall_score(test_true_labels, test_predicted_labels, average='binary', zero_division=0)
    f1 = f1_score(test_true_labels, test_predicted_labels, average='binary', zero_division=0)
    logging.warning(f'{methods}. Test: F1 Score: {f1:.2f}. Precision: {precision:.2f}, Recall: {recall:.2f}. {len(snapshot_sequence)} snapshots.')


def train_gnn(number_of_epochs=10, 
              sequence_file_name=None, 
              learning_rate=0.01, 
              batch_size=1, 
              hidden_layers=[16, 32, 16],
              model_path='models/'):

    logging.info(f'GNN training started.')

    with open(sequence_file_name, 'rb') as file:
        indexed_snapshot_sequence = pickle.load(file)
        snapshot_sequence = indexed_snapshot_sequence['snapshot_sequence']
        first_graph = snapshot_sequence[0]
        actual_num_features = first_graph.num_node_features
        train_snapshots, val_snapshots = split_snapshots(snapshot_sequence)
        model = GCN([actual_num_features] + hidden_layers + [2])
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        train_loader = DataLoader(train_snapshots, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_snapshots, batch_size=batch_size, shuffle=False)
        n_snapshots = len(snapshot_sequence)

        loss_values, val_loss_values = [], []
        logging.info(f'Training started. Number of snapshots: {n_snapshots}. Learning rate: {learning_rate}. Hidden Layers: {hidden_layers}. Batch size: {batch_size}. Number of epochs: {number_of_epochs}.')
        for epoch in range(number_of_epochs):
            start_time = time.time()
            model.train()
            epoch_loss = 0.0
            for batch in train_loader:
                optimizer.zero_grad()
                out = model(batch)
                loss = F.nll_loss(out, batch.y)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()

            epoch_loss /= len(train_loader)
            loss_values.append(epoch_loss)

            val_loss, predicted_labels, true_labels = evaluate_model(model, val_loader)
            val_loss_values.append(val_loss)
            end_time = time.time()
            logging.info(f'Epoch {epoch}: Training Loss: {epoch_loss:.4f}, Validation Loss: {val_loss:.4f}. Time: {end_time - start_time:.4f}s. Learning rate: {learning_rate}. Hidden Layers: {hidden_layers}')

        filename_root = f'hl_{hidden_layers}_n_{n_snapshots}_lr_{learning_rate}_bs_{batch_size}'
        plot_training_results(f'loss_{filename_root}.png', loss_values, val_loss_values)
        model_file_name = f'{model_path}model_{filename_root}.pt'
        torch.save(model, model_file_name)

        return model_file_name

