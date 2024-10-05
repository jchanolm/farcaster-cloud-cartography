import dash
from dash import Dash, html, dcc
import dash_cytoscape as cyto
import dash_bootstrap_components as dbc

from src.graph_viz.layout_and_styling import cyto_stylesheet
from src.graph_viz.callbacks import register_callbacks
from src.graph_viz.config import (
    DEBUG, PORT, DEFAULT_LAYOUT, CYTOSCAPE_STYLE, 
    TIME_SLIDER_MARKS, LAYOUT_OPTIONS, CYTOSCAPE_LAYOUT_SETTINGS
)

# Load extra layouts for Cytoscape
cyto.load_extra_layouts()

# Initialize the Dash app with Bootstrap stylesheet
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Define the app layout
app.layout = html.Div([
    # Header Section
    html.Div([
        html.H1(
            "Farcaster Network Visualization",
            style={
                'color': 'black',
                'display': 'inline-block',
                'margin-right': '20px'
            }
        ),
    ]),
    
    # Input and Controls Section
    html.Div([
        # User IDs Input
        html.Label(
            'Enter User IDs (comma separated):',
            style={'color': 'black'}
        ),
        dcc.Input(
            id='user-ids-input',
            type='text',
            placeholder='Enter User IDs (comma-separated)',
            style={'width': '50%'}
        ),
        
        # Build Graph Button
        html.Button(
            'Build Graph',
            id='build-graph-button',
            n_clicks=0
        ),
        
        # Layout Dropdown and Time Slider
        html.Div([
            dcc.Dropdown(
                id='layout-dropdown',
                options=LAYOUT_OPTIONS,
                value=DEFAULT_LAYOUT,
                clearable=False
            ),
            dcc.Slider(
                id='time-slider',
                min=0,
                max=100,
                value=0,
                marks=TIME_SLIDER_MARKS,
                step=None
            ),
        ]),
        
        # Cytoscape Graph Component
# Cytoscape Graph Component
    cyto.Cytoscape(
        id='cytoscape-graph',
        elements=[],
        style=CYTOSCAPE_STYLE,
        layout={
            'name': DEFAULT_LAYOUT,
            **CYTOSCAPE_LAYOUT_SETTINGS,
            'fit': False,  # Disable automatic fitting
            'zoom': 0.1,   # Set a very low zoom level
            'pan': {'x': 0, 'y': 0}  # Center the view
        },
        stylesheet=cyto_stylesheet,
        minZoom=0.05,
        maxZoom=2,
        autoungrabify=True,  # Prevent nodes from being grabbed and moved
        userZoomingEnabled=True,
        userPanningEnabled=True,
        boxSelectionEnabled=True
    ),
        # Loading Overlay with Text
        html.Div([
            dcc.Loading(
                id='loading',
                type='circle',
                fullscreen=True,
                children=html.Div([
                    # Text Above the Loading Spinner
                    html.Div(
                        "Fetching data from Farcaster...",
                        style={
                            'position': 'absolute',
                            'top': '50%',
                            'left': '50%',
                            'transform': 'translate(-50%, -60%)',
                            'fontSize': '18px',
                            'color': 'black'
                        }
                    ),
                    # Loading Output Placeholder
                    html.Div(id='loading-output')
                ], style={'position': 'relative', 'height': '100%'})
            ),
        ]),
        
        # Store Component to Hold Graph Data
        dcc.Store(id='graph-store'),
        
        # Modal for Node and Edge Metadata
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Metadata")),
                dbc.ModalBody([
                    html.Div(id='modal-body-content')
                ]),
                dbc.ModalFooter(
                    dbc.Button("Close", id="close-modal", className="ms-auto", n_clicks=0)
                ),
            ],
            id="metadata-modal",
            is_open=False,
            size="lg",
            scrollable=True,
            backdrop="static",
            centered=True,
        ),
    ])
])

# Register callbacks
register_callbacks(app)

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=DEBUG, port=PORT)