import dash
from dash import Dash, html, dcc
import dash_cytoscape as cyto
import dash_bootstrap_components as dbc

from src.graph_viz.layout_and_styling import cyto_stylesheet
from src.graph_viz.callbacks import register_callbacks
from src.graph_viz.config import (
    DEBUG, PORT, DEFAULT_LAYOUT, CYTOSCAPE_STYLE, 
    LAYOUT_OPTIONS, CYTOSCAPE_LAYOUT_SETTINGS
)

# Load extra layouts for Cytoscape
cyto.load_extra_layouts()

# Initialize the Dash app with Bootstrap stylesheet and Open Sans font
app = Dash(__name__, external_stylesheets=[
    dbc.themes.BOOTSTRAP, 
    'https://use.fontawesome.com/releases/v5.8.1/css/all.css',
    'https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;700&display=swap'
])

# Define the app layout
app.layout = html.Div([
    # Header Section with User IDs Input, Network Metrics, and Layout Algorithm Selection
    html.Div([
        html.Div([
            html.H4(
                "Cloud Cartography",
                style={
                    'color': 'black',
                    'display': 'block',
                    'margin-right': '24px',
                    'margin-left': '24px',
                    'margin-top': '12px',
                    'margin-bottom': '6px',
                    'font-family': 'Open Sans, sans-serif'
                }
            ),
            html.Div([
                dcc.Input(id='user-ids-input', type='text', placeholder='Enter FIDs (comma-separated)', style={'width': '300px', 'margin-right': '12px'}),
                html.Button('Build Graph', id='build-graph-button', n_clicks=0),
            ], style={'display': 'block', 'margin-left': '24px', 'margin-top': '6px'}),
            html.Div([
                html.I("Click nodes for account details, click edges for relationship details."),
            ], style={'text-align': 'left', 'padding': '6px', 'font-style': 'italic', 'margin-left': '24px'}),
        ], style={'display': 'inline-block', 'width': '60%'}),
        html.Div([
            html.H5("Network Metrics", style={'font-family': 'Open Sans, sans-serif', 'margin-bottom': '3px'}),
            html.Div([
                html.Div(id='node-count', style={'display': 'inline-block', 'margin-right': '12px'}),
                html.Div(id='edge-count', style={'display': 'inline-block'}),
            ]),
            html.Br(),
            html.Button('View Matrices', id='open-matrices-modal', n_clicks=0, style={'margin-top': '-14px'}),
        ], style={'display': 'inline-block', 'width': '20%', 'vertical-align': 'top', 'padding-top': '24px'}),
        html.Div([
            html.H5("Layout Algo", style={
                'margin-right': '12px',
                'font-family': 'Open Sans, sans-serif'
            }),
            html.Div([
                dcc.Dropdown(
                    id='layout-dropdown',
                    options=LAYOUT_OPTIONS,
                    value=DEFAULT_LAYOUT,
                    clearable=False,
                    style={'width': '200px', 'display': 'inline-block'}
                ),
                html.I(className="fas fa-caret-down", style={'margin-left': '-20px', 'pointer-events': 'none'})
            ], style={'display': 'inline-block', 'position': 'relative'}),
        ], style={'display': 'inline-block', 'width': '20%', 'vertical-align': 'top', 'padding-top': '24px'}),
    ], style={'margin-bottom': '12px'}),
    
    # Time Slider
    html.Div([
        dcc.Slider(id='time-slider', min=0, max=100, value=0, marks={}, step=10),
    ], style={'margin-bottom': '12px', 'padding-left': '24px'}),
    
    # Main content area
    html.Div([
        # Cytoscape Graph Component
        cyto.Cytoscape(
            id='cytoscape-graph',
            elements=[],
            style=CYTOSCAPE_STYLE,
            layout={
                'name': DEFAULT_LAYOUT,
                **CYTOSCAPE_LAYOUT_SETTINGS
            },
            stylesheet=cyto_stylesheet,
            minZoom=0.2,
            maxZoom=3,
            autoungrabify=False,
            userZoomingEnabled=True,
            userPanningEnabled=True,
            boxSelectionEnabled=True
        ),
    ], style={'height': '85vh', 'width': '100%', 'padding': '12px'}),
    
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
    
    # Modal for Node and Edge Metadata
    dbc.Modal(
    [
        dbc.ModalHeader(id="modal-header"),
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
    
    # Store Components
    dcc.Store(id='graph-store'),
    dcc.Store(id='timestamp-store'),
    
    # Loading Overlay
    html.Div([
        dcc.Loading(
            id='loading',
            type='circle',
            fullscreen=True,
            children=html.Div([
                html.Div(id='loading-output')
            ], style={'position': 'relative', 'height': '100%'})
        ),
    ]),
])

# Register callbacks
register_callbacks(app)

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=DEBUG, port=PORT)
