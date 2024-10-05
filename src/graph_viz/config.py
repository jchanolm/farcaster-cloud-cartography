# Application settings
DEBUG = True
PORT = 8050

# Graph settings
DEFAULT_LAYOUT = 'cose-bilkent'
TOP_N_NODES = 25

# Node sizes
CORE_NODE_SIZE = 112.5
NON_CORE_BASE_SIZE = 45

# Color scheme
COLORS = {
    'CORE_NODE': 'rgb(0, 255, 0)',  # Green
    'NON_CORE_NODE': 'rgb(0, 0, 255)',  # Blue
    'HIGHLIGHTED_EDGE': 'rgb(255, 0, 0)',  # Red
    'DEFAULT_NODE': '#cccccc',
    'DEFAULT_EDGE': '#999999'
}

# Edge settings
MIN_EDGE_WIDTH = 1.5
MAX_EDGE_WIDTH = 15

# Time slider settings
TIME_SLIDER_MARKS = {i: str(i) for i in range(0, 101, 10)}

# Cytoscape settings
CYTOSCAPE_STYLE = {
    'width': '100%',
    'height': '800px',
    'background-color': 'white'
}

# Layout options for dropdown
LAYOUT_OPTIONS = [
    {'label': 'Circle', 'value': 'circle'},
    {'label': 'Concentric', 'value': 'concentric'},
    {'label': 'Cose', 'value': 'cose'},
    {'label': 'Grid', 'value': 'grid'},
    {'label': 'Breadthfirst', 'value': 'breadthfirst'},
    {'label': 'Cose-Bilkent', 'value': 'cose-bilkent'},
    {'label': 'Dagre', 'value': 'dagre'},
    {'label': 'Klay', 'value': 'klay'},
]

# Cytoscape layout settings
CYTOSCAPE_LAYOUT_SETTINGS = {
    'animate': False,  # Disable animation for initial layout
    'randomize': True,  # Randomize the initial layout
    'componentSpacing': 1000,
    'nodeRepulsion': 1000000,
    'nodeOverlap': 100,
    'idealEdgeLength': 500,
    'edgeElasticity': 100,
    'nestingFactor': 1.2,
    'gravity': 0.1,
    'numIter': 5000,
    'initialTemp': 10000,
    'coolingFactor': 0.99,
    'minTemp': 1.0,
    'fit': False,  # Disable fitting
    'padding': 500
}

# Default layout settings (for backwards compatibility)
DEFAULT_LAYOUT_SETTINGS = {
    'animate': True,
    'nodeRepulsion': 50000,
    'idealEdgeLength': 827,
    'nodeDimensionsIncludeLabels': True
}