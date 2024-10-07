import dash
from dash import Input, Output, State, no_update, html
from dash.exceptions import PreventUpdate
import networkx as nx
import plotly.graph_objs as go
import numpy as np

import sys 
import os 

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph_viz.network_analysis import filter_graph, get_elements, get_adjacency_matrix, get_shortest_path_matrix
from src.data_ingestion.fetch_data import DataFetcher
from src.graph_processing.build_graph import GraphBuilder

def register_callbacks(app):
    @app.callback(
        Output('graph-store', 'data'),
        Output('loading-output', 'children'),
        Output('node-count', 'children'),
        Output('edge-count', 'children'),
        Input('build-graph-button', 'n_clicks'),
        State('user-ids-input', 'value')
    )
    def build_graph(n_clicks, user_ids_input):
        if n_clicks is None or not user_ids_input:
            raise PreventUpdate

        try:
            core_nodes = [uid.strip() for uid in user_ids_input.split(',') if uid.strip()]
            fetcher = DataFetcher()
            all_user_data = fetcher.get_all_users_data(core_nodes)
            gb = GraphBuilder()
            G = gb.build_graph_from_data(all_user_data)
            filtered_G = filter_graph(G, core_nodes)

            all_timestamps = sorted([edge[2]['timestamp'] for edge in filtered_G.edges(data=True)])
            min_timestamp, max_timestamp = min(all_timestamps), max(all_timestamps)

            graph_data = nx.readwrite.json_graph.node_link_data(filtered_G)
            graph_data['min_timestamp'] = min_timestamp
            graph_data['max_timestamp'] = max_timestamp
            graph_data['core_nodes'] = core_nodes

            node_count = filtered_G.number_of_nodes()
            edge_count = filtered_G.number_of_edges()

            return graph_data, '', f"Nodes: {node_count}", f"Edges: {edge_count}"
        except Exception as e:
            return no_update, str(e), no_update, no_update

    @app.callback(
        Output('timestamp-store', 'data'),
        Output('time-slider', 'marks'),
        Input('graph-store', 'data')
    )
    def update_timestamp_data(graph_data):
        if not graph_data:
            return {}, {}
        
        min_timestamp = graph_data['min_timestamp']
        max_timestamp = graph_data['max_timestamp']
        
        timestamp_data = {
            'min_timestamp': min_timestamp,
            'max_timestamp': max_timestamp
        }
                
        return timestamp_data, {}

    @app.callback(
        Output('cytoscape-graph', 'elements'),
        Output('node-count', 'children', allow_duplicate=True),
        Output('edge-count', 'children', allow_duplicate=True),
        Input('time-slider', 'value'),
        Input('graph-store', 'data'),
        Input('timestamp-store', 'data'),
        prevent_initial_call=True
    )
    def update_elements_and_metrics(selected_timestamp, graph_data, timestamp_data):
        if not graph_data or not timestamp_data:
            return [], "Nodes: 0", "Edges: 0"

        G = nx.readwrite.json_graph.node_link_graph(graph_data, multigraph=True)
        core_nodes = graph_data['core_nodes']

        min_timestamp = timestamp_data['min_timestamp']
        max_timestamp = timestamp_data['max_timestamp']
        actual_timestamp = min_timestamp + (selected_timestamp / 100) * (max_timestamp - min_timestamp)

        new_elements = get_elements(G, actual_timestamp, core_nodes)

        visible_nodes = set()
        visible_edges = 0
        for element in new_elements:
            if 'source' in element['data']:  # It's an edge
                visible_edges += 1
                visible_nodes.add(element['data']['source'])
                visible_nodes.add(element['data']['target'])
            else:  # It's a node
                visible_nodes.add(element['data']['id'])

        return new_elements, f"Nodes: {len(visible_nodes)}", f"Edges: {visible_edges}"

    @app.callback(
        Output('cytoscape-graph', 'layout'),
        Input('layout-dropdown', 'value')
    )
    def update_layout(layout):
        return {
            'name': layout,
            'animate': True,
            'nodeRepulsion': 51680,
            'idealEdgeLength': 827,
            'nodeDimensionsIncludeLabels': True
        }

    @app.callback(
        Output('metadata-modal', 'is_open', allow_duplicate=True),
        Output('modal-header', 'children', allow_duplicate=True),
        Output('modal-content', 'children', allow_duplicate=True),
        Input('cytoscape-graph', 'tapNodeData'),
        Input('cytoscape-graph', 'tapEdgeData'),
        Input('close-modal', 'n_clicks'),
        State('metadata-modal', 'is_open'),
        prevent_initial_call=True
    )
    def update_modal(node_data, edge_data, close_clicks, is_open):
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate

        prop_id = ctx.triggered[0]['prop_id']

        if prop_id == 'close-modal.n_clicks':
            return False, "", None  # Close modal

        elif prop_id == 'cytoscape-graph.tapNodeData':
            if node_data:
                return True, "Node Information", create_node_info(node_data)

        elif prop_id == 'cytoscape-graph.tapEdgeData':
            if edge_data:
                return True, "Edge Information", create_edge_info(edge_data)

        return is_open, dash.no_update, dash.no_update

    def create_node_info(node_data):
        username = node_data['label']
        profile_url = f"https://warpcast.com/{username}"
        profile_image_url = node_data['pfp_url']

        node_info = [
            html.Div([
                html.A(
                    html.Img(src=profile_image_url, style={'width': '50px', 'height': '50px', 'borderRadius': '50%', 'marginRight': '10px'}),
                    href=profile_url,
                    target="_blank"
                ),
                html.H3(username, style={'display': 'inline-block', 'verticalAlign': 'middle'})
            ], style={'marginBottom': '20px'}),
            html.P(f"FID: {node_data['fid']}"),
            html.P(f"Display Name: {node_data['display_name']}"),
            html.P(f"Followers: {node_data['follower_count']}"),
            html.P(f"Following: {node_data['following_count']}"),
            html.P(f"Connected Core Nodes: {node_data['connected_core_nodes']}"),
            html.P(f"Total Interactions with Core Nodes: {node_data['interactions_count']}")
        ]
        if node_data['is_core'] != 'true':
            node_info.extend([
                html.P(f"Centrality: {node_data['centrality']:.4f}"),
                html.P(f"Betweenness: {node_data['betweenness']:.4f}")
            ])
        
        node_info.append(
            html.A("View on Warpcast", href=profile_url, target="_blank", 
                style={'display': 'block', 'marginTop': '20px', 'textAlign': 'center'})
        )
        
        return node_info

    def create_edge_info(edge_data):
        source_username = edge_data['source_username']
        target_username = edge_data['target_username']
        total_interactions = edge_data['weight']
        
        edge_info = [
            html.H4(f"Interaction between {source_username} and {target_username}"),
            html.P(f"Total interactions: {total_interactions}")
        ]

        for username, node_id in [(source_username, edge_data['source']), (target_username, edge_data['target'])]:
            interactions = edge_data['interactions'][node_id]
            node_total_interactions = sum(interactions.values())
            edge_info.extend([
                html.H6(f"{username} initiated {node_total_interactions} interactions:"),
                html.Ul([
                    html.Li(f"{count} {edge_type.upper()}{'' if count == 1 else 's'}")
                    for edge_type, count in interactions.items()
                ])
            ])

        return edge_info
    
    @app.callback(
        Output('cytoscape-graph', 'zoom'),
        Output('cytoscape-graph', 'pan'),
        Input('cytoscape-graph', 'elements'),
        prevent_initial_call=True
    )   
    def adjust_zoom_on_render(elements):
        if not elements:
            return dash.no_update, dash.no_update
        return None, {'x': 0, 'y': 0}  # Let Cytoscape handle the initial zoom

    @app.callback(
        Output("matrices-modal", "is_open"),
        [Input("open-matrices-modal", "n_clicks"), Input("close-matrices-modal", "n_clicks")],
        [State("matrices-modal", "is_open")],
    )
    def toggle_matrices_modal(n1, n2, is_open):
        if n1 or n2:
            return not is_open
        return is_open

    @app.callback(
        Output('adjacency-matrix', 'figure'),
        Output('shortest-path-matrix', 'figure'),
        Input('graph-store', 'data'),
        Input('time-slider', 'value')
    )
    def update_matrices(graph_data, time_slider_value):
        if not graph_data:
            return {}, {}
        
        G = nx.readwrite.json_graph.node_link_graph(graph_data, multigraph=True)
        min_timestamp = graph_data['min_timestamp']
        max_timestamp = graph_data['max_timestamp']
        current_timestamp = min_timestamp + (time_slider_value / 100) * (max_timestamp - min_timestamp)
        
        # Filter the graph based on the current timestamp
        G_filtered = nx.Graph((u, v, d) for (u, v, d) in G.edges(data=True) if d['timestamp'] <= current_timestamp)
        
        # Ensure node attributes are copied to the filtered graph
        for node, data in G.nodes(data=True):
            if node in G_filtered:
                G_filtered.nodes[node].update(data)
        
        # Adjacency Matrix
        adj_matrix, usernames = get_adjacency_matrix(G_filtered)
        
        adj_fig = go.Figure(data=go.Heatmap(
            z=adj_matrix,
            x=usernames,
            y=usernames,
            colorscale='Viridis'
        ))
        adj_fig.update_layout(
            title='Adjacency Matrix',
            xaxis_title='Usernames',
            yaxis_title='Usernames',
            xaxis_tickangle=-45
        )
        
        # Shortest Path Matrix
        sp_matrix, usernames = get_shortest_path_matrix(G_filtered)
        
        sp_fig = go.Figure(data=go.Heatmap(
            z=sp_matrix,
            x=usernames,
            y=usernames,
            colorscale='Viridis'
        ))
        sp_fig.update_layout(
            title='Shortest Path Matrix',
            xaxis_title='Usernames',
            yaxis_title='Usernames',
            xaxis_tickangle=-45
        )
        
        return adj_fig, sp_fig
