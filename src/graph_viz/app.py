from dash import Dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import dash_cytoscape as cyto
import json
import networkx as nx
import os
from collections import Counter
import numpy as np
from datetime import datetime

cyto.load_extra_layouts()

app = Dash(__name__)

def load_graph(filename):
    filepath = os.path.join('data/processed', filename)
    with open(filepath, 'r') as f:
        graph_data = json.load(f)

    G = nx.MultiDiGraph()

    for node in graph_data['nodes']:
        node_id = node['id']
        node_attrs = node.copy()
        del node_attrs['id']
        G.add_node(node_id, **node_attrs)

    for edge in graph_data['links']:
        edge_attrs = edge.copy()
        source = edge_attrs.pop('source')
        target = edge_attrs.pop('target')
        key = edge_attrs.pop('key', None)
        G.add_edge(source, target, key=key, **edge_attrs)

    return G

def calculate_connection_strength(G, core_nodes):
    connection_strength = {}
    for node in G.nodes():
        if node not in core_nodes:
            strengths = []
            for core_node in core_nodes:
                edge_count = len(G.get_edge_data(node, core_node, default={})) + len(G.get_edge_data(core_node, node, default={}))
                strengths.append(edge_count)
            connection_strength[node] = min(strengths) if strengths else 0
    return connection_strength

def filter_graph(G, core_nodes, top_n=50):
    connection_strength = calculate_connection_strength(G, core_nodes)
    top_nodes = sorted(connection_strength, key=connection_strength.get, reverse=True)[:top_n]
    filtered_nodes = set(top_nodes + core_nodes)
    return G.subgraph(filtered_nodes).copy()

G = load_graph('graph_988_378_190000_746.json')
core_nodes = ['988', '378', '190000', '746']
filtered_G = filter_graph(G, core_nodes)

# Remove user dwr (id "3") from the graph if it exists
if "3" in filtered_G:
    filtered_G.remove_node("3")

# Calculate centrality and betweenness for non-core nodes only
non_core_nodes = [node for node in filtered_G.nodes() if node not in core_nodes]
non_core_subgraph = filtered_G.subgraph(non_core_nodes)
centrality = nx.degree_centrality(non_core_subgraph)
betweenness = nx.betweenness_centrality(non_core_subgraph)

# Get all timestamps and sort them
all_timestamps = sorted([edge[2]['timestamp'] for edge in filtered_G.edges(data=True)])
min_timestamp, max_timestamp = min(all_timestamps), max(all_timestamps)

# Adjust timestamps to be indexed from Jan 2020
jan_2020_timestamp = 1577836800  # Unix timestamp for Jan 1, 2020 00:00:00 UTC
min_timestamp = min_timestamp - jan_2020_timestamp
max_timestamp = max_timestamp - jan_2020_timestamp

def normalize_value(value, min_val, max_val, new_min, new_max):
    if max_val == min_val:
        return new_min
    return ((value - min_val) / (max_val - min_val)) * (new_max - new_min) + new_min

def get_elements_at_timestamp(G, timestamp):
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
                key = (source, target)
                if key not in edge_dict:
                    edge_dict[key] = {
                        'data': {
                            'source': source,
                            'target': target,
                            'weight': 1,
                            'edge_types': Counter([edge_type])
                        }
                    }
                else:
                    edge_dict[key]['data']['weight'] += 1
                    edge_dict[key]['data']['edge_types'][edge_type] += 1

    # Normalize edge weights and increase thickness for relationships with lots of interactions
    if edge_dict:
        max_weight = max(edge['data']['weight'] for edge in edge_dict.values())
        for edge in edge_dict.values():
            normalized_weight = normalize_value(edge['data']['weight'], 1, max_weight, 1.5, 15)  # Increased max thickness by 2x
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

    # Determine N based on timestamp
    N = min((timestamp - min_timestamp + 1), 5)
    top_N_nodes = sorted_nodes[:N]

    # Mark edges connected to top N non-core nodes
    for edge_key, edge in edge_dict.items():
        source = edge['data']['source']
        target = edge['data']['target']
        if (source in top_N_nodes and target in core_nodes) or (target in top_N_nodes and source in core_nodes):
            edge['data']['highlight'] = 'true'
        else:
            edge['data']['highlight'] = 'false'

    # Calculate node metrics for non-core nodes
    max_centrality = max(centrality.values()) if centrality else 1
    max_betweenness = max(betweenness.values()) if betweenness else 1

    for node in active_nodes:
        data = G.nodes[node]
        is_core = node in core_nodes

        # Calculate the number of core nodes this node is connected to
        connected_core_nodes = sum(1 for core_node in core_nodes if temp_G.has_edge(node, core_node))
        
        # Size nodes based on how many core nodes they're connected to
        if is_core:
            node_size = 112.5  # Base size for core nodes
        else:
            base_size = 45  # Base size for non-core nodes
            size_multiplier = 1 + (connected_core_nodes - 1) * 0.5  # Linear increase: 1, 1.5, 2, 2.5, ...
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

        cyto_elements.append({
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
        })

    # Only include edges if it's not the initial stage
    if timestamp > min_timestamp:
        cyto_elements.extend(list(edge_dict.values()))

    return cyto_elements, temp_G

app.layout = html.Div([
    html.H1("Farcaster Network Visualization"),
    html.Div([
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
                min=min_timestamp,
                max=max_timestamp,
                value=min_timestamp,
                marks={str(ts): str(ts + jan_2020_timestamp) for ts in range(min_timestamp, max_timestamp + 1, max(1, (max_timestamp - min_timestamp) // 10))},
                step=None
            ),
            cyto.Cytoscape(
                id='cytoscape-graph',
                elements=get_elements_at_timestamp(filtered_G, min_timestamp)[0],
                style={'width': '100%', 'height': '800px'},
                layout={
                    'name': 'cose-bilkent',
                    'animate': False,
                    'nodeRepulsion': 51680,  # Increased by 50% from 34453
                    'idealEdgeLength': 827,  # Increased by 50% from 551
                    'nodeDimensionsIncludeLabels': True
                },
                stylesheet=[
                    # Default node style (dimmed)
                    {
                        'selector': 'node',
                        'style': {
                            'content': 'data(label)',
                            'font-size': '32px',  # Increased from 26.25px
                            'text-opacity': 1,  # Changed from 0.5 to 1
                            'text-valign': 'center',
                            'text-halign': 'center',
                            'background-color': '#cccccc',  # Light gray
                            'width': 'data(size)',
                            'height': 'data(size)',
                            'color': '#ffffff',
                            'text-outline-color': '#000000',
                            'text-outline-width': 3  # Increased from 2
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
                            'opacity': 0.2,  # Dimmed edges
                            'curve-style': 'bezier',
                            'line-color': '#999999',  # Light gray
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
            )
        ], style={'width': '80%', 'display': 'inline-block', 'vertical-align': 'top'}),
        html.Div([
            html.Div(id='node-data'),
            html.Div(id='edge-data')
        ], style={'width': '20%', 'display': 'inline-block', 'vertical-align': 'top'})
    ])
])

@app.callback(
    Output('cytoscape-graph', 'layout'),
    Input('layout-dropdown', 'value')
)
def update_layout(layout):
    return {
        'name': layout,
        'animate': True,
        'nodeRepulsion': 51680,  # Increased by 50% from 34453
        'idealEdgeLength': 827,  # Increased by 50% from 551
        'nodeDimensionsIncludeLabels': True
    }

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

@app.callback(
    Output('edge-data', 'children'),
    Input('cytoscape-graph', 'tapEdgeData')
)
def display_edge_data(data):
    if not data:
        return "Click on an edge to see its details"
    edge_types = data.get('edge_types', {})
    return html.Div([
        html.H3(f"Edge: {data['source']} -> {data['target']}"),
        html.P(f"Total Weight: {data['weight']}"),
        html.P(f"Normalized Weight: {data['normalized_weight']:.2f}"),
        html.H4("Edge Type Counts:"),
        html.Ul([html.Li(f"{edge_type}: {count}") for edge_type, count in edge_types.items()])
    ])

@app.callback(
    Output('cytoscape-graph', 'elements'),
    [Input('time-slider', 'value'),
     Input('cytoscape-graph', 'tapNodeData')]
)
def update_graph(selected_timestamp, tapNodeData):
    selected_node_id = tapNodeData['id'] if tapNodeData else None
    elements, temp_G = get_elements_at_timestamp(filtered_G, selected_timestamp)

    if selected_node_id:
        highlighted_edges = set()
        highlighted_nodes = set()
        for core_node in core_nodes:
            try:
                path = nx.shortest_path(temp_G, source=selected_node_id, target=core_node)
                highlighted_nodes.update(path)
                path_edges = list(zip(path[:-1], path[1:]))
                highlighted_edges.update(path_edges)
            except nx.NetworkXNoPath:
                pass
        # Update elements
        for element in elements:
            data = element['data']
            if 'source' in data and 'target' in data:
                source = data['source']
                target = data['target']
                if (source, target) in highlighted_edges or (target, source) in highlighted_edges:
                    data['edge_to_core'] = 'true'
                else:
                    data['edge_to_core'] = 'false'
            else:
                node_id = data['id']
                if node_id in highlighted_nodes:
                    data['node_to_core'] = 'true'
                else:
                    data['node_to_core'] = 'false'
    else:
        # No node selected
        for element in elements:
            data = element['data']
            if 'edge_to_core' in data:
                data['edge_to_core'] = 'false'
            if 'node_to_core' in data:
                data['node_to_core'] = 'false'

    if selected_timestamp == min_timestamp:
        # Only show core nodes if at the initial timestamp
        elements = [element for element in elements if element['data'].get('is_core') == 'true' or 'source' not in element['data']]
    return elements

if __name__ == '__main__':
    app.run_server(debug=True)
