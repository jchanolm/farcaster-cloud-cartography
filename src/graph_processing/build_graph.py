import os
import json
import logging
from typing import List, Dict, Optional

import networkx as nx
import pandas as pd

from src.data_ingestion.fetch_data import DataFetcher

class GraphBuilder:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.data_fetcher = DataFetcher()

    def create_edges(self, G, fid, node_data, edge_type):
        if edge_type not in node_data:
            return

        df = pd.DataFrame(node_data[edge_type])
        if df.empty:
            return

        df['source'] = df['source'].astype(str)
        df['target'] = df['target'].astype(str)
        df['edge_type'] = edge_type.upper()

        edge_attr_columns = ['edge_type', 'timestamp']
        if 'target_hash' in df.columns:
            edge_attr_columns.append('target_hash')

        G.add_edges_from(nx.from_pandas_edgelist(
            df,
            source='source',
            target='target',
            edge_attr=edge_attr_columns,
            create_using=nx.MultiDiGraph
        ).edges(data=True))

        self.logger.info(f"Added {len(df)} {edge_type.upper()} edges for FID {fid}")

    def build_graph_from_data(self, all_user_data: Dict[str, Dict]) -> nx.MultiDiGraph:
        G = nx.MultiDiGraph()
        total_nodes_created = 0

        # First, add nodes and their attributes
        for fid, user_data in all_user_data.items():
            # Add core node
            core_metadata = user_data['core_node_metadata']
            G.add_node(fid, **core_metadata)
            total_nodes_created += 1

            # Add connections metadata
            for node in user_data.get("connections_metadata", []):
                if not G.has_node(node['fid']):
                    G.add_node(node['fid'], **node)
                    total_nodes_created += 1

        self.logger.info(f"Created {total_nodes_created} unique nodes.")

        # Then, add edges
        for fid, user_data in all_user_data.items():
            self.create_edges(G, fid, user_data, 'likes')
            self.create_edges(G, fid, user_data, 'recasts')
            self.create_edges(G, fid, user_data, 'casts')
            self.create_edges(G, fid, user_data, 'following')

        self.logger.info(f"Graph has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
        return G

    def calculate_connection_strength(self, G, core_nodes):
        connection_strength = {}
        for node in G.nodes():
            if node not in core_nodes:
                strengths = []
                for core_node in core_nodes:
                    edge_count = (
                        len(G.get_edge_data(node, core_node, default={}))
                        + len(G.get_edge_data(core_node, node, default={}))
                    )
                    strengths.append(edge_count)
                connection_strength[node] = min(strengths) if strengths else 0
        return connection_strength

    def filter_graph(self, G, core_nodes, top_n=25):
        connection_strength = self.calculate_connection_strength(G, core_nodes)
        top_nodes = sorted(connection_strength, key=connection_strength.get, reverse=True)[:top_n]
        filtered_nodes = set(top_nodes + core_nodes)
        return G.subgraph(filtered_nodes).copy()

    def build_and_filter_graph(self, fids: List[str]) -> nx.MultiDiGraph:
        all_user_data = self.data_fetcher.get_all_users_data(fids)
        G = self.build_graph_from_data(all_user_data)
        filtered_G = self.filter_graph(G, fids)
        return filtered_G

    def save_graph_as_json(self, G, fids, output_dir="data/processed"):
        os.makedirs(output_dir, exist_ok=True)
        graph_data = nx.node_link_data(G)
        filename = f"graph_{'_'.join(fids)}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(graph_data, f)
        
        self.logger.info(f"Graph saved as JSON to {filepath}")

if __name__ == "__main__":
    # Example usage
    gb = GraphBuilder()
    test_fids = ['190000', '190001']  # Example FIDs
    filtered_graph = gb.build_and_filter_graph(test_fids)
    gb.save_graph_as_json(filtered_graph, test_fids)
    print(f"Built and saved graph for FIDs: {test_fids}")
    print(f"Graph has {filtered_graph.number_of_nodes()} nodes and {filtered_graph.number_of_edges()} edges")