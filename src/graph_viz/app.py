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
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, 'https://use.fontawesome.com/releases/v5.8.1/css/all.css'])

# Define the app layout
app.layout = html.Div([
    # Header Section
    html.Div([
        html.H2(
            "Cloud Cartography - Farcaster",
            style={
                'color': 'black',
                'display': 'inline-block',
                'margin-right': '20px'
            }
        ),
    ]),
    
    # Main content area
    html.Div([
        # Left column: Input, Controls, and Graph
        html.Div([
            # User IDs Input
            html.Label('Enter User IDs (comma separated):', style={'color': 'black'}),
            dcc.Input(id='user-ids-input', type='text', placeholder='Enter User IDs (comma-separated)', style={'width': '50%', 'margin-bottom': '20px'}),
            html.Button('Build Graph', id='build-graph-button', n_clicks=0, style={'margin-bottom': '20px'}),
            
            # Layout Algorithm Selection
            html.H4("Select Layout Algorithm [Optional]", style={'margin-top': '20px', 'margin-bottom': '10px'}),
            dcc.Dropdown(id='layout-dropdown', options=LAYOUT_OPTIONS, value=DEFAULT_LAYOUT, clearable=False, style={'margin-bottom': '10px'}),
            
            # Time Slider
            dcc.Slider(id='time-slider', min=0, max=100, value=0, marks=TIME_SLIDER_MARKS, step=None),
            
            # Cytoscape Graph Component
            cyto.Cytoscape(
                id='cytoscape-graph',
                elements=[],
                style=CYTOSCAPE_STYLE,
                layout={'name': DEFAULT_LAYOUT, **CYTOSCAPE_LAYOUT_SETTINGS, 'fit': False, 'zoom': 0.05, 'pan': {'x': 0, 'y': 0}},
                stylesheet=cyto_stylesheet,
                minZoom=0.05,
                maxZoom=2,
                autoungrabify=True,
                userZoomingEnabled=True,
                userPanningEnabled=True,
                boxSelectionEnabled=True
            ),
        ], style={'width': '70%', 'display': 'inline-block', 'vertical-align': 'top'}),
        
        # Right column: Metrics
        html.Div([
            html.H4("Network Metrics"),
            html.Div(id='node-count', style={'margin-bottom': '10px'}),
            html.Div(id='edge-count', style={'margin-bottom': '10px'}),
            html.Button('View Matrices', id='open-matrices-modal', n_clicks=0, style={'margin-top': '20px'}),
        ], style={'width': '30%', 'display': 'inline-block', 'vertical-align': 'top', 'padding-left': '20px'}),
    ]),

    # Scroll down indicator
    html.Div([
        html.I(className="fas fa-chevron-down"),
        html.Span("Scroll for more", style={'margin-left': '10px'})
    ], style={'text-align': 'center', 'margin-top': '20px', 'margin-bottom': '20px'}),
    
    # Matrices Modal
    dbc.Modal([
        dbc.ModalHeader("Network Matrices"),
        dbc.ModalBody([
            html.Div([
                html.H5("Adjacency Matrix"),
                dcc.Graph(id='adjacency-matrix'),
                html.H5("Shortest Path Matrix"),
                dcc.Graph(id='shortest-path-matrix'),
            ])
        ]),
        dbc.ModalFooter(
            dbc.Button("Close", id="close-matrices-modal", className="ml-auto")
        ),
    ], id="matrices-modal", size="xl"),
    
    # Store Component to Hold Graph Data
    dcc.Store(id='graph-store'),
    
    # Loading Overlay with Text
    html.Div([
        dcc.Loading(
            id='loading',
            type='circle',
            fullscreen=True,
            children=html.Div([
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
                html.Div(id='loading-output')
            ], style={'position': 'relative', 'height': '100%'})
        ),
    ]),
    
    # Modal for Node and Edge Metadata
    dbc.Modal(
    [
        dbc.ModalBody([
            html.Div(id='modal-content')
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

# Register callbacks
register_callbacks(app)

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=DEBUG, port=PORT)