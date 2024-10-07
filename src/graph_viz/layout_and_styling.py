from src.graph_viz.config import (
    COLORS, DEFAULT_LAYOUT, DEFAULT_LAYOUT_SETTINGS,
    LAYOUT_OPTIONS, CORE_NODE_SIZE, NON_CORE_BASE_SIZE
)

# Cytoscape stylesheet
cyto_stylesheet = [
    # Default node style (dimmed)
    {
        'selector': 'node',
        'style': {
            'content': 'data(label)',
            'font-size': '32px',
            'text-opacity': 1,
            'text-valign': 'center',
            'text-halign': 'center',
            'background-color': COLORS['DEFAULT_NODE'],
            'width': 'data(size)',
            'height': 'data(size)',
            'color': '#000000',
            'text-outline-color': '#ffffff',
            'text-outline-width': 3
            
        }
    },
    {
    'selector': '.fade',
    'style': {
        'transition-property': 'opacity',
        'transition-duration': '0.5s',
        'transition-timing-function': 'ease-in-out-cubic'
    }
    },
    # Add this to the existing cyto_stylesheet list
    {
        'selector': '.fade',
        'style': {
            'transition-property': 'opacity',
            'transition-duration': '0.5s',
            'transition-timing-function': 'ease-in-out-cubic'
        }
    },
    {
    'selector': 'node[total_core_interactions > 0]',
    'style': {
        'border-width': '3px',
        'border-color': '#FFD700'  # Gold color for nodes with core interactions
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
            'background-color': '#8A2BE2',  # Warpcast purple
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
            'line-color': COLORS['DEFAULT_EDGE'],
            'target-arrow-color': COLORS['DEFAULT_EDGE'],
            'target-arrow-shape': 'triangle',
            'arrow-scale': 0.5
        }
    },
    # Highlighted edges (along paths to core nodes)
    {
        'selector': 'edge[edge_to_core = "true"]',
        'style': {
            'line-color': COLORS['HIGHLIGHTED_EDGE'],
            'width': 'data(normalized_weight)',
            'opacity': 1.0,
            'target-arrow-color': COLORS['HIGHLIGHTED_EDGE'],
            'target-arrow-shape': 'triangle',
            'arrow-scale': 1
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

# Default layout options
default_layout = {
    'name': DEFAULT_LAYOUT,
    'animate': True,
    'animationDuration': 500,
    'animationEasing': 'ease-in-out-cubic',
    'nodeRepulsion': 35000,
    'idealEdgeLength': 100,
    'nodeDimensionsIncludeLabels': True,
    'fit': True,
    'padding': 30,
    'randomize': False
}

# Layout options are now imported directly from config.py
layout_options = LAYOUT_OPTIONS

# You might want to add these functions here if they're not already in network_analysis.py
def get_node_size(is_core, connected_core_nodes):
    if is_core:
        return CORE_NODE_SIZE
    else:
        return NON_CORE_BASE_SIZE * (1 + (connected_core_nodes - 1) * 0.25)

def get_node_color(is_core, betweenness, max_betweenness):
    if is_core:
        return '#8A2BE2'  # Warpcast purple
    elif max_betweenness > 0:
        return f"rgb({int(255 * betweenness / max_betweenness)}, 0, 255)"
    else:
        return COLORS['NON_CORE_NODE']