import argparse
import logging
from animator import create_animation
from instance_creator import create_instance
from simulator import produce_training_data_parallel
from gnn_trainer import train_gnn

# Initialize parser
parser = argparse.ArgumentParser(description='Run different modes of the security simulation program.')

# Adding arguments
parser.add_argument('mode', choices=['create_instance', 'produce_training_data', 'train_gnn', 'animate', 'evaluate'], help='Mode of operation')
parser.add_argument('--instance_type', default='static', choices=['static', 'dynamic'], help='Type of instance to create')
parser.add_argument('--size', default='small', choices=['small', 'medium', 'large'], help='Size of the graph')
parser.add_argument('--game_time', type=int, default=70, help='Time horizon for the simulation')
parser.add_argument('--n_simulations', type=int, default=128, help='Number of simulations to run')
parser.add_argument('--log_window', type=int, default=3, help='Size of the logging window')
parser.add_argument('--random_cyber_agent_seed', default=None, help='Seed for random cyber agent')
parser.add_argument('--number_of_epochs', type=int, default=8, help='Number of epochs for GNN training')
parser.add_argument('--learning_rate', type=float, default=0.005, help='Learning rate for GNN training')
parser.add_argument('--batch_size', type=int, default=256, help='Batch size for GNN training')
parser.add_argument('--hidden_layers', nargs='+', type=int, default=[64, 64], help='Hidden layers configuration for GNN')
parser.add_argument('--rddl_path', default='content/', help='Path to the RDDL files')
parser.add_argument('--tmp_path', default='tmp/', help='Temporary file path')
parser.add_argument('--snapshot_sequence_path', default='snapshot_sequences/', help='Path to snapshot sequences')
parser.add_argument('--training_sequence_file_name', default='snapshot_sequences/latest20231127_192822.pkl', help='Filename for training sequence')
parser.add_argument('--animation_sequence_filename', default='snapshot_sequences/latest20231127_191906.pkl', help='Filename for animation sequence')
parser.add_argument('--animation_predictor_filename', default='models/model_hl_[64, 64]_n_6287_lr_0.005_bs_256.pt', help='Filename for the animation predictor model')
parser.add_argument('--animation_predictor_type', default='gnn', choices=['gnn', 'tabular', 'none'], help='Type of animation predictor')

# Parse arguments
args = parser.parse_args()

# Set up logging
logging.basicConfig(filename='log.log', level=logging.DEBUG, format='%(asctime)s - %(message)s')
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.warning('\n\n')

max_start_time_step = args.log_window + int((args.game_time - args.log_window) / 2)
max_log_steps_after_total_compromise = int(args.log_window / 2)

# Modes
if args.mode == 'create_instance':
    # TODO: Write graph_index to file 
    logging.info(f'Creating new instance specification.')
    rddl_file_path, graph_index_file_path = create_instance(instance_type=args.instance_type, size=args.size, horizon=args.game_time, rddl_path=args.rddl_path)
    s = f'Instance specification written to {rddl_file_path}. Graph index written to {graph_index_file_path}.'
    logging.info(s)
    print(s)

elif args.mode == 'produce_training_data':
    logging.info(f'Producing training data.')
    sequence_file_name = produce_training_data_parallel(
        n_simulations=args.n_simulations, 
        log_window=args.log_window, 
        max_start_time_step=max_start_time_step, 
        max_log_steps_after_total_compromise=max_log_steps_after_total_compromise,
        rddl_path=args.rddl_path, 
        tmp_path=args.tmp_path,
        snapshot_sequence_path=args.snapshot_sequence_path,
        random_cyber_agent_seed=args.random_cyber_agent_seed)
    s = f'Training data produced and written to {sequence_file_name}.'
    logging.info(s)
    print(s)

elif args.mode == 'train_gnn':
    logging.info(f'Training GNN.')
    test_true_labels, test_predicted_labels, predictor_filename = train_gnn(
                    number_of_epochs=args.number_of_epochs, 
                    sequence_file_name=args.training_sequence_file_name, 
                    learning_rate=args.learning_rate, 
                    batch_size=args.batch_size, 
                    hidden_layers=args.hidden_layers)
    s = f'GNN trained. Model written to {predictor_filename}.'
    logging.info(s)
    print(s)

elif args.mode == 'animate':
    logging.info(f'Creating animation.')
    create_animation(animation_sequence_filename=args.animation_sequence_filename, 
                     predictor_type=args.animation_predictor_type, 
                     predictor_filename=args.animation_predictor_filename)
    s = f'Animation written to file network_animation.gif.'
    logging.info(s)
    print(s)
