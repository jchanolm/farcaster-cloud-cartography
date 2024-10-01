from dash import Dash
from dash import html, dcc 
from dash.dependencies import Input, Output, State
import dash_cytoscape as cyto
import json 
import networkx as nx 
import os 
from collections import Counter
import numpy as np

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

G = load_graph('graph_988_746_190000_378.json')
core_nodes = ['988', '746', '190000', '378']
filtered_G = filter_graph(G, core_nodes)

# Remove user dwr (id "3") from the graph if it exists
if "3" in filtered_G:
    filtered_G.remove_node("3")

connection_strength = calculate_connection_strength(filtered_G, core_nodes)
max_strength = max(connection_strength.values()) if connection_strength else 1

# Calculate centrality and betweenness
centrality = nx.degree_centrality(filtered_G)
betweenness = nx.betweenness_centrality(filtered_G)

# Get all timestamps and sort them
all_timestamps = sorted([edge[2]['timestamp'] for edge in filtered_G.edges(data=True)])
min_timestamp, max_timestamp = min(all_timestamps), max(all_timestamps)

def normalize_value(value, min_val, max_val, new_min, new_max):
    if max_val == min_val:
        return new_min
    return ((value - min_val) / (max_val - min_val)) * (new_max - new_min) + new_min

def get_elements_at_timestamp(G, timestamp, prev_timestamp=None):
    cyto_elements = []
    active_nodes = set(core_nodes)  # Initialize with core nodes

    edge_dict = {}
    for edge in G.edges(data=True):
        if edge[2]['timestamp'] <= timestamp:
            source = str(edge[0])
            target = str(edge[1])
            active_nodes.add(source)
            active_nodes.add(target)
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

    # Normalize edge weights
    if edge_dict:
        max_weight = max(edge['data']['weight'] for edge in edge_dict.values())
        for edge in edge_dict.values():
            normalized_weight = normalize_value(edge['data']['weight'], 1, max_weight, 0.5, 3)
            edge['data']['normalized_weight'] = normalized_weight

    # Calculate node metrics
    node_degree = dict(filtered_G.degree(active_nodes))
    max_degree = max(node_degree.values()) if node_degree else 1
    max_centrality = max(centrality.values()) if centrality else 1
    max_betweenness = max(betweenness.values()) if betweenness else 1

    for node in active_nodes:
        data = G.nodes[node]
        is_core = node in core_nodes

        # Size nodes based on centrality and betweenness
        if is_core:
            node_size = 40  # Increased from 30 to 40
        else:
            centrality_factor = normalize_value(centrality.get(node, 0), 0, max_centrality, 0, 1)
            betweenness_factor = normalize_value(betweenness.get(node, 0), 0, max_betweenness, 0, 1)
            node_size = normalize_value(centrality_factor + betweenness_factor, 0, 2, 20, 80)

        # Color nodes based on betweenness centrality
        node_color = f"rgb({int(255 * betweenness.get(node, 0) / max_betweenness)}, 0, 255)"

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
                'centrality': centrality.get(node, 0),
                'betweenness': betweenness.get(node, 0),
                'color': node_color
            }
        })

    # Only include edges if it's not the initial stage
    if timestamp > min_timestamp:
        cyto_elements.extend(list(edge_dict.values()))

    return cyto_elements

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
                marks={str(ts): str(ts) for ts in range(min_timestamp, max_timestamp + 1, max(1, (max_timestamp - min_timestamp) // 10))},
                step=None
            ),
            cyto.Cytoscape(
                id='cytoscape-graph',
                elements=get_elements_at_timestamp(filtered_G, min_timestamp),
                style={'width': '100%', 'height': '800px'},
                layout={
                    'name': 'cose-bilkent',
                    'animate': False,
                    'nodeRepulsion': 20000,  # Decreased from 25000 to 20000 (20% reduction)
                    'idealEdgeLength': 320,  # Decreased from 400 to 320 (20% reduction)
                    'nodeDimensionsIncludeLabels': True
                },
                stylesheet=[
                    {
                        'selector': 'node',
                        'style': {
                            'content': 'data(label)',
                            'font-size': '10px',
                            'text-opacity': 0.8,
                            'text-valign': 'center',
                            'text-halign': 'center',
                            'background-color': '#808080',  # Set non-core nodes to gray
                            'width': 'data(size)',
                            'height': 'data(size)',
                            'color': '#ffffff',
                            'text-outline-color': '#000000',
                            'text-outline-width': 2
                        }
                    },
                    {
                        'selector': 'node[is_core = "true"]',
                        'style': {
                            'background-color': '#00ff00'
                        }
                    },
                    {
                        'selector': 'edge',
                        'style': {
                            'width': 'data(normalized_weight)',
                            'opacity': 0.6,
                            'curve-style': 'bezier',
                            'line-color': '#000000'
                        }
                    }
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
        'nodeRepulsion': 20000,  # Decreased from 25000 to 20000 (20% reduction)
        'idealEdgeLength': 320,  # Decreased from 400 to 320 (20% reduction)
        'nodeDimensionsIncludeLabels': True
    }

@app.callback(
    Output('node-data', 'children'),
    Input('cytoscape-graph', 'tapNodeData')
)
def display_node_data(data):
    if not data:
        return "Click on a node to see its details"
    return html.Div([
        html.H3(f"User: {data['label']}"),
        html.P(f"FID: {data['fid']}"),
        html.P(f"Display Name: {data['display_name']}"),
        html.P(f"Followers: {data['follower_count']}"),
        html.P(f"Following: {data['following_count']}"),
        html.P(f"Centrality: {data['centrality']:.4f}"),
        html.P(f"Betweenness: {data['betweenness']:.4f}")
    ])

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
    Input('time-slider', 'value')
)
def update_graph(selected_timestamp):
    return get_elements_at_timestamp(filtered_G, selected_timestamp)

if __name__ == '__main__':
    app.run_server(debug=True)