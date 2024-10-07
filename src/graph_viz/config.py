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
    'animate': True,  # Enable animation for smoother transitions
    'animationDuration': 100,  # Animation duration in milliseconds
    'animationEasing': 'ease-in-out-cubic',  # Easing function for smoother animation
    'randomize': False,  # Disable randomization for more predictable layouts
    'componentSpacing': 300,  # Further reduced for tighter layout
    'nodeRepulsion': 10000,  # Further reduced for less aggressive node separation
    'nodeOverlap': 30,  # Further reduced to allow some overlap
    'idealEdgeLength': 100,  # Further reduced for tighter layout
    'edgeElasticity': 30,  # Reduced for more flexible edges
    'nestingFactor': 1.05,  # Slightly reduced nesting factor
    'gravity': 0.3,  # Increased gravity for more compact layout
    'numIter': 2000,  # Slightly reduced iterations
    'initialTemp': 3000,  # Reduced initial temperature
    'coolingFactor': 0.97,  # Slightly increased cooling factor for smoother cooling
    'minTemp': 1.0,
    'fit': True,
    'padding': 20  # Further reduced padding
}

# Default layout settings (for backwards compatibility)
DEFAULT_LAYOUT_SETTINGS = {
    'animate': True,
    'animationDuration': 100,
    'animationEasing': 'ease-in-out-cubic',
    'nodeRepulsion': 20000,
    'idealEdgeLength': 500,
    'nodeDimensionsIncludeLabels': True
}
