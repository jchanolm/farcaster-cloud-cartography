from dash import Dash
from dash import html, dcc 
from dash.dependencies import Input, Output
import dash_cytoscape as cyto
import json 
import networkx as nx 
import os 


cyto.load_extra_layouts()

app = Dash(__name__)


def load_graph(filename):
    filepath = os.path.join('data/processed', filename)
    with open(filepath, 'r') as f:
        graph_data = json.load(f)

    # Create a MultiDiGraph
    G = nx.MultiDiGraph()

    # Add nodes
    for node in graph_data['nodes']:
        node_id = node['id']
        node_attrs = node.copy()
        del node_attrs['id']
        G.add_node(node_id, **node_attrs)

    # Add edges
    for edge in graph_data['links']:
        edge_attrs = edge.copy()
        source = edge_attrs.pop('source')
        target = edge_attrs.pop('target')
        key = edge_attrs.pop('key', None)
        G.add_edge(source, target, key=key, **edge_attrs)

    return G

def filter_graph(G, core_nodes):
    filtered_nodes = set()
    for node in G.nodes():
        if all(node in G.neighbors(core_node) for core_node in core_nodes) and node not in core_nodes:
            filtered_nodes.add(node)
    filtered_nodes.update(core_nodes)  # Ensure core nodes are included
    return G.subgraph(filtered_nodes)

G = load_graph('graph_988_746.json')
core_nodes = ['988', '746']
filtered_G = filter_graph(G, core_nodes)

cyto_elements = []

for node, data in filtered_G.nodes(data=True):
    cyto_elements.append({
        'data': {
            'id': str(node),
            'label': data.get('username', str(node)),
            'size': data.get('follower_count', 10),
            'fid': str(node),
            'display_name': data.get('username', 'N/A'),
            'follower_count': data.get('follower_count', 0),
            'following_count': data.get('following_count', 0)
        }
    })

for edge in filtered_G.edges():
    if edge[0] != edge[1]:  # Remove self edges
        cyto_elements.append({
            'data': {'source': str(edge[0]), 'target': str(edge[1])}
        })

app.layout = html.Div([
    html.H1("Farcaster Network Visualization"),
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
    cyto.Cytoscape(
        id='cytoscape-graph',
        elements=cyto_elements,
        style={'width': '100%', 'height': '600px'},
        layout={
            'name': 'cose-bilkent'
        },
        stylesheet=[
            {
                'selector': 'node',
                'style': {
                    'content': 'data(label)',
                    'font-size': '8px',
                    'text-opacity': 0.7,
                    'text-valign': 'center',
                    'text-halign': 'right',
                    'background-color': '#4287f5',
                    'width': 'mapData(size, 0, 1000, 10, 60)',
                    'height': 'mapData(size, 0, 1000, 10, 60)'
                }
            },
            {
                'selector': 'edge',
                'style': {
                    'width': 1,
                    'opacity': 0.6,
                    'curve-style': 'bezier'
                }
            }
        ]
    ),
    html.Div(id='node-data')
])

@app.callback(
    Output('cytoscape-graph', 'layout'),
    Input('layout-dropdown', 'value')
)
def update_layout(layout):
    return {
        'name': layout,
        'animate': True
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
        html.P(f"Following: {data['following_count']}")
    ])

if __name__ == '__main__':
    app.run_server(debug=True)
