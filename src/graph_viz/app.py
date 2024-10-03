import os
import json
from collections import Counter
from datetime import datetime

import networkx as nx
import numpy as np
from dash import Dash, html, dcc, Input, Output, State, no_update
from dash.exceptions import PreventUpdate
import dash_cytoscape as cyto

from src.data_ingestion.fetch_data import DataFetcher
from src.graph_processing.build_graph import GraphBuilder

# Load extra layouts for Cytoscape
cyto.load_extra_layouts()

# Initialize the Dash app
app = Dash(__name__)

# Define utility functions
def calculate_connection_strength(G, core_nodes):
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

def filter_graph(G, core_nodes, top_n=50):
    connection_strength = calculate_connection_strength(G, core_nodes)
    top_nodes = sorted(connection_strength, key=connection_strength.get, reverse=True)[:top_n]
    filtered_nodes = set(top_nodes + core_nodes)
    return G.subgraph(filtered_nodes).copy()

jan_2020_timestamp = 1577836800  # Unix timestamp for Jan 1, 2020 00:00:00 UTC

def normalize_value(value, min_val, max_val, new_min, new_max):
    if max_val == min_val:
        return new_min
    return ((value - min_val) / (max_val - min_val)) * (new_max - new_min) + new_min

def get_elements(G, timestamp, core_nodes, tapNodeData=None):
    cyto_elements = []
    active_nodes = set(core_nodes)  # Initialize with core nodes

    edge_dict = {}
    edges_up_to_timestamp = []
    for edge in G.edges(data=True):
        if edge[2]['timestamp'] - jan_2020_timestamp <= timestamp:
            source = str(edge[0])
            target = str(edge[1])
            active_nodes.add(source)
            active_nodes.add(target)
            edges_up_to_timestamp.append(edge)
            if source != target:
                edge_type = edge[2].get('edge_type', 'Unknown')
                key = tuple(sorted((source, target)))  # Ensure consistent ordering
                if key not in edge_dict:
                    edge_dict[key] = {
                        'data': {
                            'source': source,
                            'target': target,
                            'weight': 1,
                            'edge_types': Counter([edge_type]),
                            'edge_to_core': 'false'  # Default value
                        }
                    }
                else:
                    edge_dict[key]['data']['weight'] += 1
                    edge_dict[key]['data']['edge_types'][edge_type] += 1

    # Normalize edge weights and increase thickness for relationships with lots of interactions
    if edge_dict:
        max_weight = max(edge['data']['weight'] for edge in edge_dict.values())
        for edge in edge_dict.values():
            normalized_weight = normalize_value(
                edge['data']['weight'], 1, max_weight, 1.5, 15
            )  # Increased max thickness by 2x
            edge['data']['normalized_weight'] = normalized_weight

    # Build a temporary graph up to the current timestamp
    temp_G = nx.Graph()
    temp_G.add_nodes_from(active_nodes)
    temp_G.add_edges_from([(e[0], e[1]) for e in edges_up_to_timestamp])

    # Calculate connection strength for non-core nodes
    connection_strength = {}
    for node in temp_G.nodes():
        if node not in core_nodes:
            strengths = []
            for core_node in core_nodes:
                if temp_G.has_edge(node, core_node):
                    edge_count = temp_G.number_of_edges(node, core_node)
                    strengths.append(edge_count)
                else:
                    strengths.append(0)
            connection_strength[node] = min(strengths) if strengths else 0

    # Sort non-core nodes by their connection strength to core nodes
    sorted_nodes = sorted(connection_strength, key=connection_strength.get, reverse=True)

    # Get all timestamps and sort them
    all_timestamps = sorted([edge[2]['timestamp'] for edge in G.edges(data=True)])
    min_timestamp, max_timestamp = min(all_timestamps), max(all_timestamps)

    # Adjust timestamps to be indexed from Jan 2020
    min_timestamp = min_timestamp - jan_2020_timestamp
    max_timestamp = max_timestamp - jan_2020_timestamp

    # Determine N based on timestamp
    N = min(int(normalize_value(timestamp, min_timestamp, max_timestamp, 1, 5)), 5)
    top_N_nodes = sorted_nodes[:N]

    # Mark edges connected to top N non-core nodes
    for edge_key, edge in edge_dict.items():
        source = edge['data']['source']
        target = edge['data']['target']
        if (source in top_N_nodes and target in core_nodes) or (
            target in top_N_nodes and source in core_nodes
        ):
            edge['data']['edge_to_core'] = 'true'
        else:
            edge['data']['edge_to_core'] = 'false'

    # Calculate node metrics for non-core nodes
    centrality = nx.degree_centrality(temp_G)
    betweenness = nx.betweenness_centrality(temp_G)
    max_centrality = max(centrality.values()) if centrality else 1
    max_betweenness = max(betweenness.values()) if betweenness else 1

    for node in active_nodes:
        data = G.nodes[node]
        is_core = node in core_nodes

        # Calculate the number of core nodes this node is connected to
        connected_core_nodes = sum(
            1 for core_node in core_nodes if temp_G.has_edge(node, core_node)
        )

        # Size nodes based on how many core nodes they're connected to
        if is_core:
            node_size = 112.5  # Base size for core nodes
        else:
            base_size = 45  # Base size for non-core nodes
            size_multiplier = 1 + (connected_core_nodes - 1) * 0.5  # Linear increase
            node_size = base_size * size_multiplier

        # Color nodes
        if is_core:
            node_color = "rgb(0, 255, 0)"  # Green color for core nodes
        else:
            # Color non-core nodes based on betweenness centrality
            if max_betweenness > 0:
                node_color = f"rgb({int(255 * betweenness.get(node, 0) / max_betweenness)}, 0, 255)"
            else:
                node_color = "rgb(0, 0, 255)"  # Default color if max_betweenness is 0

        cyto_elements.append(
            {
                'data': {
                    'id': node,
                    'label': data.get('username', node),
                    'size': node_size,
                    'fid': node,
                    'display_name': data.get('username', 'N/A'),
                    'follower_count': data.get('follower_count', 0),
                    'following_count': data.get('following_count', 0),
                    'is_core': 'true' if is_core else 'false',
                    'centrality': centrality.get(node, 0) if not is_core else 'N/A',
                    'betweenness': betweenness.get(node, 0) if not is_core else 'N/A',
                    'color': node_color,
                    'connected_core_nodes': connected_core_nodes
                }
            }
        )

    # Only include edges if it's not the initial stage (timestamp > min_timestamp)
    if timestamp > min_timestamp:
        cyto_elements.extend(list(edge_dict.values()))

    # If a node is selected, highlight paths to core nodes
    if tapNodeData:
        selected_node_id = tapNodeData['id']
        highlighted_edges = set()
        highlighted_nodes = set()
        for core_node in core_nodes:
            try:
                path = nx.shortest_path(temp_G, source=selected_node_id, target=core_node)
                highlighted_nodes.update(path)
                path_edges = list(zip(path[:-1], path[1:]))
                highlighted_edges.update(path_edges)
            except nx.NetworkXNoPath:
                pass  # If no path exists, skip

        # Update elements for highlighting
        for element in cyto_elements:
            data = element['data']
            if 'source' in data and 'target' in data:  # It's an edge
                source = data['source']
                target = data['target']
                if (source, target) in highlighted_edges or (target, source) in highlighted_edges:
                    data['edge_to_core'] = 'true'
                else:
                    data['edge_to_core'] = 'false'
            else:  # It's a node
                node_id = data['id']
                if node_id in highlighted_nodes:
                    data['node_to_core'] = 'true'
                else:
                    data['node_to_core'] = 'false'

    # If it's the initial timestamp (min_timestamp), only show core nodes
    if timestamp <= min_timestamp:
        cyto_elements = [
            element for element in cyto_elements
            if element['data'].get('is_core') == 'true'
        ]

    return cyto_elements

# Define the app layout
app.layout = html.Div([
    html.Div([
        html.H1("Farcaster Network Visualization", style={'color': 'black', 'display': 'inline-block', 'margin-right': '20px'}),
    ]),
    html.Div([
        html.Label('Enter User IDs (comma separated):', style={'color': 'black'}),
        dcc.Input(
            id='user-ids-input',
            type='text',
            placeholder='Enter User IDs (comma-separated)',
            style={'width': '50%'}
        ),
        html.Button('Build Graph', id='build-graph-button', n_clicks=0),
        html.Div([
            dcc.Dropdown(
                id='layout-dropdown',
                options=[
                    {'label': 'Circle', 'value': 'circle'},
                    {'label': 'Concentric', 'value': 'concentric'},
                    {'label': 'Cose', 'value': 'cose'},
                    {'label': 'Grid', 'value': 'grid'},
                    {'label': 'Breadthfirst', 'value': 'breadthfirst'},
                    {'label': 'Cose-Bilkent', 'value': 'cose-bilkent'},
                    {'label': 'Dagre', 'value': 'dagre'},
                    {'label': 'Klay', 'value': 'klay'},
                ],
                value='cose-bilkent',
                clearable=False
            ),
            dcc.Slider(
                id='time-slider',
                min=0,
                max=100,
                value=0,
                marks={i: str(i) for i in range(0, 101, 10)},
                step=None
            ),
        ]),
        # Cytoscape component
        cyto.Cytoscape(
            id='cytoscape-graph',
            elements=[],
            style={'width': '100%', 'height': '800px', 'background-color': 'white'},
            layout={
                'name': 'cose-bilkent',
                'animate': False,
                'nodeRepulsion': 51680,
                'idealEdgeLength': 827,
                'nodeDimensionsIncludeLabels': True
            },
            stylesheet=[
                # Default node style (dimmed)
                {
                    'selector': 'node',
                    'style': {
                        'content': 'data(label)',
                        'font-size': '32px',
                        'text-opacity': 1,
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'background-color': '#cccccc',
                        'width': 'data(size)',
                        'height': 'data(size)',
                        'color': '#000000',
                        'text-outline-color': '#ffffff',
                        'text-outline-width': 3
                    }
                },
                # Highlighted nodes (along paths to core nodes)
                {
                    'selector': 'node[node_to_core = "true"]',
                    'style': {
                        'background-color': 'data(color)',
                    }
                },
                # Core nodes
                {
                    'selector': 'node[is_core = "true"]',
                    'style': {
                        'background-color': '#00ff00',
                        'shape': 'star',
                    }
                },
                # Default edge style (dimmed)
                {
                    'selector': 'edge',
                    'style': {
                        'width': 'data(normalized_weight)',
                        'opacity': 0.2,
                        'curve-style': 'bezier',
                        'line-color': '#999999',
                        'target-arrow-color': '#999999',
                        'target-arrow-shape': 'triangle',
                        'arrow-scale': 0.5
                    }
                },
                # Highlighted edges (along paths to core nodes)
                {
                    'selector': 'edge[edge_to_core = "true"]',
                    'style': {
                        'line-color': '#ff0000',
                        'width': 'data(normalized_weight)',
                        'opacity': 1.0,
                        'target-arrow-color': '#ff0000',
                        'target-arrow-shape': 'triangle',
                        'arrow-scale': 0.7
                    }
                },
                # Edge hover style
                {
                    'selector': 'edge:hover',
                    'style': {
                        'line-color': '#000000',
                        'transition-property': 'line-color',
                        'transition-duration': '0.5s',
                        'target-arrow-color': '#000000',
                        'target-arrow-shape': 'triangle',
                        'arrow-scale': 0.5
                    }
                },
            ]
        ),
        html.Div([
            html.Div(id='node-data', style={'color': 'black'}),
            html.Div(id='edge-data', style={'color': 'black'})
        ], style={'width': '20%', 'display': 'inline-block', 'vertical-align': 'top'})
    ]),
    # Add a dcc.Loading component that wraps an html.Div which will be updated during the build_graph callback
    dcc.Loading(
        id='loading',
        type='circle',
        fullscreen=True,
        children=html.Div(id='loading-output')
    ),
    # Store component to hold graph data
    dcc.Store(id='graph-store'),
])

# Callback to build the graph and store data
@app.callback(
    [Output('graph-store', 'data'),
     Output('loading-output', 'children')],
    Input('build-graph-button', 'n_clicks'),
    State('user-ids-input', 'value'),
    prevent_initial_call=True
)
def build_graph(n_clicks, user_ids_input):
    if n_clicks is None or not user_ids_input:
        return no_update, no_update

    try:
        core_nodes = [uid.strip() for uid in user_ids_input.split(',') if uid.strip()]

        # Fetch data using user-provided IDs
        fetcher = DataFetcher()
        all_user_data = fetcher.get_all_users_data(core_nodes)

        # Build graph from fetched data
        gb = GraphBuilder()
        G = gb.build_graph_from_data(all_user_data)

        # Filter the graph based on core nodes
        filtered_G = filter_graph(G, core_nodes)

        # Get all timestamps and sort them
        all_timestamps = sorted([edge[2]['timestamp'] for edge in filtered_G.edges(data=True)])
        min_timestamp, max_timestamp = min(all_timestamps), max(all_timestamps)

        # Adjust timestamps to be indexed from Jan 2020
        min_timestamp = min_timestamp - jan_2020_timestamp
        max_timestamp = max_timestamp - jan_2020_timestamp

        # Convert the graph to a JSON serializable format
        graph_data = nx.readwrite.json_graph.node_link_data(filtered_G)
        graph_data['min_timestamp'] = min_timestamp
        graph_data['max_timestamp'] = max_timestamp

        # Update the loading-output div (can be empty string)
        return graph_data, ''

    except Exception as e:
        # In case of error, handle the exception
        return no_update, ''

# Callback to update Cytoscape elements based on graph data, slider, and node taps
@app.callback(
    Output('cytoscape-graph', 'elements'),
    [Input('time-slider', 'value'),
     Input('cytoscape-graph', 'tapNodeData'),
     Input('graph-store', 'data')],
    State('user-ids-input', 'value')
)
def update_elements(selected_timestamp, tapNodeData, graph_data, user_ids_input):
    if not graph_data:
        return []

    # Reconstruct the graph
    G = nx.readwrite.json_graph.node_link_graph(graph_data, multigraph=True)

    core_nodes = [uid.strip() for uid in user_ids_input.split(',') if uid.strip()]

    min_timestamp = graph_data['min_timestamp']
    max_timestamp = graph_data['max_timestamp']

    # Calculate the actual timestamp based on the slider value
    actual_timestamp = min_timestamp + (selected_timestamp / 100) * (max_timestamp - min_timestamp)

    # Get elements at the adjusted timestamp
    cyto_elements = get_elements(G, actual_timestamp, core_nodes, tapNodeData)

    return cyto_elements

# Callback to update Cytoscape layout based on dropdown
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

# Callback to display node data
@app.callback(
    Output('node-data', 'children'),
    Input('cytoscape-graph', 'tapNodeData')
)
def display_node_data(data):
    if not data:
        return "Click on a node to see its details"
    node_info = [
        html.H3(f"User: {data['label']}"),
        html.P(f"FID: {data['fid']}"),
        html.P(f"Display Name: {data['display_name']}"),
        html.P(f"Followers: {data['follower_count']}"),
        html.P(f"Following: {data['following_count']}"),
        html.P(f"Connected Core Nodes: {data['connected_core_nodes']}")
    ]
    if data['is_core'] != 'true':
        node_info.extend([
            html.P(f"Centrality: {data['centrality']:.4f}"),
            html.P(f"Betweenness: {data['betweenness']:.4f}")
        ])
    return html.Div(node_info)

# Callback to display edge data
@app.callback(
    Output('edge-data', 'children'),
    Input('cytoscape-graph', 'tapEdgeData')
)
def display_edge_data(data):
    if not data:
        return "Click on an edge to see its details"
    edge_types = data.get('edge_types', {})
    return html.Div([
        html.H3(f"Edge: {data['source']} → {data['target']}"),
        html.P(f"Total Weight: {data['weight']}"),
        html.P(f"Normalized Weight: {data['normalized_weight']:.2f}"),
        html.H4("Edge Type Counts:"),
        html.Ul([html.Li(f"{edge_type}: {count}") for edge_type, count in edge_types.items()])
    ])

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)
