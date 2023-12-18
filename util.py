import io
import torch
import random
from google.cloud import storage


def get_sequence_filenames(bucket_manager, sequence_dir_path, min_nodes, max_nodes, log_window, max_sequences, n_validation_sequences):
    # TODO: #1 Now filtering by exact log window, but should select all above log_window, as they are truncate later anyhow.
    prefix = f'{sequence_dir_path}log_window_{log_window}/'
    log_window_filtered_filenames = [blob.name for blob in bucket_manager.bucket.list_blobs(prefix=prefix)]
    node_num_filtered_filenames = [fn for fn in log_window_filtered_filenames if int(fn.split('/')[2].split('_')[0]) >= min_nodes and int(fn.split('/')[2].split('_')[0]) <= max_nodes]
    random.shuffle(node_num_filtered_filenames)
    if max_sequences + n_validation_sequences > len(node_num_filtered_filenames):
        raise ValueError(f'Not enough sequences for training and validation. {len(node_num_filtered_filenames)} sequences found, but {max_sequences} (training) + {n_validation_sequences} (validation) requested.')
    return node_num_filtered_filenames[:max_sequences], node_num_filtered_filenames[max_sequences:max_sequences+n_validation_sequences] # Limit the number of sequences to max_sequences

