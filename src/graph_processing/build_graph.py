import os
import json
import pickle
import logging
from typing import List, Dict, Optional
from datetime import datetime 

import networkx as nx
import pandas as pd

from src.data_ingestion.fetch_data import DataFetcher

class GraphBuilder:
    def __init__(self, data_dir: str = 'data/raw/', processed_dir: str = 'data/processed/'):
        """
        Initializes the GraphBuilder instance.

        Parameters:
        - data_dir (str): Directory where raw data is stored.
        - processed_dir (str): Directory where processed data will be saved.
        """
        self.data_dir = data_dir
        self.processed_dir = processed_dir
        os.makedirs(self.processed_dir, exist_ok=True)
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)


    def load_data(self, fid: str) -> Optional[Dict]:
        filepath = os.path.join(self.data_dir, f'user_{fid}_data.json')
        with open(filepath, 'r') as f:
            fid_data = json.load(f)
        return fid_data
    

    def create_edges_for_likes(self, G, fid, node_data):
        likes_data = node_data.get('likes', [])
        likes_df = pd.DataFrame(likes_data)
        likes_df['source'] = fid
        likes_df = likes_df.rename(columns={
            'target_fid': 'target'
        })
        likes_df['source'] = fid
        likes_df['edge_type'] = 'LIKED'
        edge_attr_columns = ['edge_type', 'timestamp']
        G.add_edges_from(nx.from_pandas_edgelist(
            likes_df,
            source='source',
            target='target',
            edge_attr=edge_attr_columns,
            create_using=nx.MultiDiGraph()
        ).edges(data=True))

        logging.info(f"Added {len(likes_df)} LIKE edges for FID {fid}")
    


    def create_edges_for_followers(self, G, fid, node_data):
        followers_data = node_data.get('followers', [])
        followers_df = pd.DataFrame(followers_data)
        edge_attr_columns = ['edge_type', 'timestamp']
        G.add_edges_from(nx.from_pandas_edgelist(
            followers_df, 
            source='source',
            target='target',
            edge_attr=edge_attr_columns,
            create_using=nx.MultiDiGraph()
        ).edges(data=True))

        logging.info(f"Added {len(followers_df)} incoming FOLLOWS edges for FID {fid}")


    def create_edges_for_following(self, G, fid, node_data):
        follows_data = node_data.get('follows', [])
        follows_df = pd.DataFrame(follows_data)
        edge_attr_columns = ['edge_type', 'timestamp']
        G.add_edges_from(nx.from_pandas_edgelist(
            follows_df, 
            source='source',
            target='target',
            edge_attr=edge_attr_columns,
            create_using=nx.MultiDiGraph()
        ).edges(data=True))

        logging.info(f"Added {len(follows_df)} outgoing FOLLOWS edges for FID {fid}")


    def create_edges_for_recasts(self, G, fid, node_data):
        recasts_data = node_data.get('recasts', [])
        recasts_df = pd.DataFrame(recasts_data)
        edge_attr_columns = ['edge_type', 'timestamp', 'target_hash']
        G.add_edges_from(nx.from_pandas_edgelist(
            recasts_df,
            source='source',
            target='target',
            edge_attr=edge_attr_columns,
            create_using=nx.MultiDiGraph
        ).edges(data=True))

        logging.info(f"Added {len(recasts_df)} RECASTED edges for FID {fid}")

        # def add_edges_from_likes(self, G, fid, node_data):
        # # Extract likes data into a list of dictionaries
        # likes_data = node_data.get('likes', [])
        
        # # Create a DataFrame from the likes data
        # likes_df = pd.DataFrame(likes_data)
        
        # # Add the source FID to the DataFrame
        # likes_df['source_fid'] = fid
        
        # # Rename columns to match our desired edge attributes
        # likes_df = likes_df.rename(columns={
        #     'target_fid': 'target',
        #     'source_fid': 'source',
        #     'timestamp': 'timestamp',
        #     'target_hash': 'target_hash'
        # })
        
        # Add an edge_type column
        # likes_df['edge_type'] = 'like'
        
        # # Select only the columns we want to use as edge attributes
        # edge_attr_df = likes_df[['source', 'target', 'edge_type', 'timestamp', 'target_hash']]
        
        # # Convert DataFrame rows to a list of tuples (source, target, attr_dict)
        # edge_tuples = [
        #     (row['source'], row['target'], row.to_dict())
        #     for _, row in edge_attr_df.iterrows()
        # ]
        
        # # Add edges to the graph
        # G.add_edges_from(edge_tuples)
        
        # print(f"Added {len(edge_tuples)} like edges for FID {fid}")

    def build_graph(self, fids):
        G = nx.MultiDiGraph()
        total_nodes_created = 0
        for fid in fids:
            node_data = self.load_data(fid)
            for node in node_data["connections_metadata"]:
                if not G.has_node(node['fid']):
                    G.add_node(node['fid'], 
                               username=node['username'],
                               display_name=node['display_name'],
                               pfp_url=node['pfp_url'],
                               follower_count=node['follower_count'],
                               following_count=node['following_count'])
                    total_nodes_created += 1
        logging.info(f"Created {total_nodes_created} unique nodes across all FIDs: {fids}")
        for fid in fids:
            node_data = self.load_data(fid)
            self.create_edges_for_likes(G, fid, node_data)
            self.create_edges_for_followers(G, fid, node_data)
            self.create_edges_for_following(G, fid, node_data)
            self.create_edges_for_recasts(G, fid, node_data)
        logging.info(f"Graph has {G.number_of_nodes()} nodes")
        logging.info(f"Graph has {G.number_of_edges()} edges")
        return G            
        


    

if __name__ == "__main__":
    gb = GraphBuilder()
    gb.build_graph(['746', '190000'])



    #     for fid in fids:
    #         data = self.load_data(fid)
    #         if data:
    #             G.add_node(fid, **data.get('attributes', {}))
    #             connections = data.get('connections', [])
    #             for connection in connections:
    #                 if connection in fids:
    #                     G.add_edge(fid, connection)

    #     self.save_graph(G, time_value)
    #     return G

    # def save_graph(self, G: nx.Graph, time_value: int) -> None:
    #     """
    #     Saves the graph to a pickle file.

    #     Parameters:
    #     - G (nx.Graph): The graph to save.
    #     - time_value (int): The time point associated with the graph.
    #     """
    #     filepath = os.path.join(self.processed_dir, f'graph_t{time_value}.pkl')
    #     with open(filepath, 'wb') as f:
    #         pickle.dump(G, f)
    #     self.logger.info(f"Graph for time {time_value} saved to {filepath}.")

    # def load_graph(self, time_value: int) -> Optional[nx.Graph]:
    #     """
    #     Loads a graph from a pickle file.

    #     Parameters:
    #     - time_value (int): The time point of the graph to load.

    #     Returns:
    #     - Optional[nx.Graph]: The loaded graph, or None if not found.
    #     """
    #     filepath = os.path.join(self.processed_dir, f'graph_t{time_value}.pkl')
    #     if os.path.exists(filepath):
    #         with open(filepath, 'rb') as f:
    #             G = pickle.load(f)
    #         return G
    #     else:
    #         self.logger.warning(f"No graph found for time {time_value}.")
    #         return None

    # def load_data(self, fid: str) -> Optional[Dict]:
    #     """
    #     Loads raw data for a given FID.

    #     Parameters:
    #     - fid (str): The Farcaster user ID.

    #     Returns:
    #     - Optional[Dict]: The loaded data, or None if not found.
    #     """
    #     data_fetcher = DataFetcher(data_dir=self.data_dir)
    #     return data_fetcher.load_data(fid)

    # def compute_degree_centrality(self, G: nx.Graph) -> Dict[str, float]:
    #     """
    #     Computes degree centrality for all nodes in the graph.

    #     Parameters:
    #     - G (nx.Graph): The graph to analyze.

    #     Returns:
    #     - Dict[str, float]: A dictionary of node IDs to their degree centrality.
    #     """
    #     return nx.degree_centrality(G)

    # # Add more methods for other metrics and analyses as needed