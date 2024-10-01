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
        likes_df['source'] = str(fid)
        likes_df = likes_df.rename(columns={
            'target_fid': 'target'
        })
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


    def create_edges_for_casts(self, G, fid, node_data):
        casts_data = node_data.get('casts', [])
        casts_df = pd.DataFrame(casts_data)
        print(casts_df.head())
        edge_attr_columns = ['edge_type', 'timestamp']
        G.add_edges_from(nx.from_pandas_edgelist(
            casts_df,
            source='source',
            target='target',
            edge_attr=edge_attr_columns,
            create_using=nx.MultiDiGraph
        ).edges(data=True))

        logging.info(f"Added {len(casts_df)} REPLIED edges for FID {fid}")

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
            # self.create_edges_for_followers(G, fid, node_data)
            # self.create_edges_for_following(G, fid, node_data)
            self.create_edges_for_recasts(G, fid, node_data)
            self.create_edges_for_casts(G, fid, node_data)
        logging.info(f"Graph has {G.number_of_nodes()} nodes")
        logging.info(f"Graph has {G.number_of_edges()} edges")
        return G            
        
    def save_graph_as_json(self, G, fids):
        graph_data = nx.node_link_data(G)
        filename = f"graph_{'_'.join(fids)}.json"
        filepath = os.path.join(self.processed_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(graph_data, f)
        
        logging.info(f"Graph saved as JSON to {filepath}")


if __name__ == "__main__":
    gb = GraphBuilder()
    fids = ['988', '746']
    graph = gb.build_graph(fids)
    gb.save_graph_as_json(graph, fids)