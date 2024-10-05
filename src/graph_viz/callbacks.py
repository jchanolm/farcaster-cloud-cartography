import dash
from dash import Input, Output, State, no_update, html
from dash.exceptions import PreventUpdate
import networkx as nx

from src.graph_viz.network_analysis import filter_graph, get_elements
from src.data_ingestion.fetch_data import DataFetcher
from src.graph_processing.build_graph import GraphBuilder

def register_callbacks(app):
    @app.callback(
        [Output('graph-store', 'data'),
         Output('loading-output', 'children')],
        Input('build-graph-button', 'n_clicks'),
        State('user-ids-input', 'value'),
        prevent_initial_call=True
    )
    def build_graph(n_clicks, user_ids_input):
        if n_clicks is None or not user_ids_input:
            return no_update, no_update

        try:
            core_nodes = [uid.strip() for uid in user_ids_input.split(',') if uid.strip()]

            # Fetch data using user-provided IDs
            fetcher = DataFetcher()
            all_user_data = fetcher.get_all_users_data(core_nodes)

            # Build graph from fetched data
            gb = GraphBuilder()
            G = gb.build_graph_from_data(all_user_data)

            # Filter the graph based on core nodes
            filtered_G = filter_graph(G, core_nodes)

            # Get all timestamps and sort them
            all_timestamps = sorted([edge[2]['timestamp'] for edge in filtered_G.edges(data=True)])
            min_timestamp, max_timestamp = min(all_timestamps), max(all_timestamps)

            # Convert the graph to a JSON serializable format
            graph_data = nx.readwrite.json_graph.node_link_data(filtered_G)
            graph_data['min_timestamp'] = min_timestamp
            graph_data['max_timestamp'] = max_timestamp

            # Update the loading-output div (can be empty string)
            return graph_data, ''

        except Exception as e:
            # In case of error, handle the exception
            return no_update, ''

    @app.callback(
        Output('cytoscape-graph', 'elements'),
        [Input('time-slider', 'value'),
         Input('cytoscape-graph', 'tapNodeData'),
         Input('graph-store', 'data')],
        State('user-ids-input', 'value')
    )
    def update_elements(selected_timestamp, tapNodeData, graph_data, user_ids_input):
        if not graph_data:
            return []

        # Reconstruct the graph
        G = nx.readwrite.json_graph.node_link_graph(graph_data, multigraph=True)

        core_nodes = [uid.strip() for uid in user_ids_input.split(',') if uid.strip()]

        min_timestamp = graph_data['min_timestamp']
        max_timestamp = graph_data['max_timestamp']

        # Calculate the actual timestamp based on the slider value
        actual_timestamp = min_timestamp + (selected_timestamp / 100) * (max_timestamp - min_timestamp)

        # Get elements at the adjusted timestamp
        new_elements = get_elements(G, actual_timestamp, core_nodes, tapNodeData)

        # Add transition animation to each element
        for element in new_elements:
            if 'position' not in element:
                element['position'] = {'x': 0, 'y': 0}
            element['classes'] = 'fade'

        return new_elements

    @app.callback(
        Output('cytoscape-graph', 'layout'),
        Input('layout-dropdown', 'value')
    )
    def update_layout(layout):
        return {
            'name': layout,
            'animate': True,
            'nodeRepulsion': 51680,
            'idealEdgeLength': 827,
            'nodeDimensionsIncludeLabels': True
        }

    @app.callback(
        [Output('metadata-modal', 'is_open'),
         Output('modal-body-content', 'children')],
        [Input('cytoscape-graph', 'tapNodeData'),
         Input('cytoscape-graph', 'tapEdgeData'),
         Input('close-modal', 'n_clicks')],
        [State('metadata-modal', 'is_open'),
         State('graph-store', 'data')]
    )
    def display_metadata(node_data, edge_data, close_clicks, is_open, graph_data):
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update, no_update
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if trigger_id == 'close-modal':
            return False, no_update

        if edge_data:
            source = edge_data['source']
            target = edge_data['target']
            
            # Find the nodes in graph_data that match the source and target IDs
            source_node = next((node for node in graph_data['nodes'] if node['id'] == source), None)
            target_node = next((node for node in graph_data['nodes'] if node['id'] == target), None)
            
            if source_node and target_node:
                edge_info = [
                    html.H3(f"Edge: {source_node['username']} ↔ {target_node['username']}"),
                    html.P(f"Total Interactions: {edge_data['weight']}")
                ]

                for user, node in [(source, source_node), (target, target_node)]:
                    interactions = edge_data['interactions'][user]
                    total_interactions = sum(interactions.values())
                    edge_info.extend([
                        html.H4(f"Username {node['username']}:"),
                        html.P(f"{total_interactions} interactions initiated by {node['username']}"),
                        html.Ul([
                            html.Li(f"{count} {edge_type.lower()}{'s' if count > 1 else ''}")
                            for edge_type, count in interactions.items()
                        ])
                    ])

                return True, html.Div(edge_info)
            else:
                return True, html.Div([html.P("Error: Unable to find node data")])

        elif node_data:
            node_info = [
                html.H3(f"User: {node_data['label']}"),
                html.P(f"FID: {node_data['fid']}"),
                html.P(f"Display Name: {node_data['display_name']}"),
                html.P(f"Followers: {node_data['follower_count']}"),
                html.P(f"Following: {node_data['following_count']}"),
                html.P(f"Connected Core Nodes: {node_data['connected_core_nodes']}")
            ]
            if node_data['is_core'] != 'true':
                node_info.extend([
                    html.P(f"Centrality: {node_data['centrality']:.4f}"),
                    html.P(f"Betweenness: {node_data['betweenness']:.4f}")
                ])
            return True, html.Div(node_info)

        return no_update, no_update

    @app.callback(
        Output('cytoscape-graph', 'zoom'),
        Output('cytoscape-graph', 'pan'),
        Input('cytoscape-graph', 'elements'),
        prevent_initial_call=True
    )
    def adjust_zoom_on_render(elements):
        if not elements:
            return dash.no_update, dash.no_update
        return 0.1, {'x': 0, 'y': 0}