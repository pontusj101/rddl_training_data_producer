import networkx as nx
import logging
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import torch
import pickle
from simulator import produce_training_data_parallel

class Predictor:
    def __init__(self, predictor_type, file_name):
        self.predictor_type = predictor_type
        if predictor_type == 'gnn':
            self.model = torch.load(file_name)
            self.model.eval()
        elif predictor_type == 'tabular':
            with open(file_name, 'rb') as file:
                self.snapshot_sequence = pickle.load(file)
    
    def frequency(self, target_log_sequence, snapshot_sequence):
        n_labels = len(snapshot_sequence[0].y)
        count = torch.zeros(n_labels)
        hits = torch.zeros(n_labels)
        for snapshot in snapshot_sequence:
            log_sequence = snapshot.x[:, 1:]
            if torch.equal(log_sequence, target_log_sequence):
                for label_index in range(n_labels):
                    count[label_index] += 1
                    labels = snapshot.y
                    if labels[label_index] == 1:
                        hits[label_index] += 1
        return torch.round(torch.nan_to_num(hits/count))


    def predict(self, snapshot):
        if self.predictor_type == 'gnn':
            out = self.model(snapshot)
            return out.max(1)[1]
        elif self.predictor_type == 'tabular':
            return self.frequency(snapshot.x[:, 1:], self.snapshot_sequence)


def create_graph(snapshot):
    G = nx.Graph()
    edge_index = snapshot.edge_index.numpy()
    node_status = snapshot.y.numpy()
    node_type = snapshot.x[:, 0].numpy()  # Assuming 1 for host, 0 for credentials

    for i in range(edge_index.shape[1]):
        G.add_edge(edge_index[0, i], edge_index[1, i])

    for node, status in enumerate(node_status):
        G.nodes[node]['status'] = status
        G.nodes[node]['type'] = node_type[node]

    return G

def update_graph(num, snapshots, pos, ax, predictor):
    ax.clear()
    snapshot = snapshots[num]

    prediction = predictor.predict(snapshot)

    G = create_graph(snapshot)

    # Separate nodes by type
    host_nodes = [node for node, attr in G.nodes(data=True) if attr['type'] == 1]
    credential_nodes = [node for node, attr in G.nodes(data=True) if attr['type'] == 0]

    color_grey = '#C0C0C0'
    color_orange = '#FFCC99'
    color_red = '#FF9999'
    color_yellow = '#FFFF99'

    # Update node colors based on their status
    color_map_host = []
    for node in host_nodes:
        status = G.nodes[node]['status']
        pred = prediction[node].item()  # Assuming prediction is a tensor, use .item() to get the value

        if pred == 1 and status == 0:
            color = color_red
        elif pred == 1 and status == 1:
            color = color_orange
        elif pred == 0 and status == 1:
            color = color_yellow
        else:  # pred == 0 and status == 0
            color = color_grey

        color_map_host.append(color)

    color_map_credential = []
    for node in credential_nodes:
        status = G.nodes[node]['status']
        pred = prediction[node].item()  # Assuming prediction is a tensor, use .item() to get the value

        if pred == 1 and status == 0:
            color = color_red
        elif pred == 1 and status == 1:
            color = color_orange
        elif pred == 0 and status == 1:
            color = color_yellow
        else:  # pred == 0 and status == 0
            color = color_grey

        color_map_credential.append(color)

    # Draw nodes separately according to their type
    nx.draw_networkx_nodes(G, pos, nodelist=host_nodes, node_color=color_map_host, node_shape='s', ax=ax)
    nx.draw_networkx_nodes(G, pos, nodelist=credential_nodes, node_color=color_map_credential, node_shape='o', ax=ax)

    # Draw edges and labels
    nx.draw_networkx_edges(G, pos, ax=ax)
    nx.draw_networkx_labels(G, pos, ax=ax)

    ax.set_title(f"Step {num}")

def create_animation(snapshot_sequence, predictor_type, predictor_filename):

    predictor = Predictor(predictor_type, predictor_filename)

    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Calculate layout once
    G_initial = create_graph(snapshot_sequence[0])
    pos = nx.spring_layout(G_initial)  # You can use other layouts as well

    ani = animation.FuncAnimation(fig, update_graph, frames=len(snapshot_sequence), 
                                fargs=(snapshot_sequence, pos, ax, predictor), interval=1000)
    ani.save('network_animation.gif', writer='pillow', fps=25)


def animate_snapshot_sequence(predictor_type, predictor_filename, graph_index=None):
    n_completely_compromised, snapshot_sequence, predictor_filename = produce_training_data_parallel(use_saved_data=False, 
                                                        n_simulations=1, 
                                                        log_window=16, 
                                                        game_time=500,
                                                        max_start_time_step=266, 
                                                        max_log_steps_after_total_compromise=8,
                                                        graph_index=graph_index, 
                                                        rddl_path='content/', 
                                                        random_cyber_agent_seed=None)

    create_animation(snapshot_sequence, predictor_type, predictor_filename=predictor_filename)