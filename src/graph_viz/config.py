import datetime 

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

# Cytoscape settings
CYTOSCAPE_STYLE = {
    'width': '100%',
    'height': '85vh',
    'background-color': 'white'
}

# Layout options for dropdown
LAYOUT_OPTIONS = [
    {'label': 'Circle', 'value': 'circle'},
    {'label': 'Grid', 'value': 'grid'},
    {'label': 'Breadthfirst', 'value': 'breadthfirst'},
    {'label': 'Cose-Bilkent [Default]', 'value': 'cose-bilkent'},
]

# Cytoscape layout settings
CYTOSCAPE_LAYOUT_SETTINGS = {
    'animate': False,  # Disable animation for initial layout
    'randomize': True,  # Randomize the initial layout
    'componentSpacing': 500,  # Reduced from 1000
    'nodeRepulsion': 15000,  # Reduced from 25000
    'nodeOverlap': 50,  # Reduced from 100
    'idealEdgeLength': 125,  # Reduced from 500
    'edgeElasticity': 50,  # Reduced from 100
    'nestingFactor': 1.1,  # Reduced from 1.2
    'gravity': 0.2,  # Increased from 0.1
    'numIter': 2500,  # Reduced from 5000
    'initialTemp': 5000,  # Reduced from 10000
    'coolingFactor': 0.95,  # Reduced from 0.99
    'minTemp': 1.0,
    'fit': True,
    'padding': 30  # Reduced from 500
}

# Default layout settings (for backwards compatibility)
DEFAULT_LAYOUT_SETTINGS = {
    'animate': True,
    'nodeRepulsion': 25000,
    'idealEdgeLength': 827,
    'nodeDimensionsIncludeLabels': True
}
