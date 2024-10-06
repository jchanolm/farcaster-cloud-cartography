import networkx as nx
from collections import Counter

def calculate_connection_strength(G, core_nodes):
    connection_strength = {}
    for node in G.nodes():
        if node not in core_nodes:
            strengths = []
            for core_node in core_nodes:
                edge_count = (
                    len(G.get_edge_data(node, core_node, default={}))
                    + len(G.get_edge_data(core_node, node, default={}))
                )
                strengths.append(edge_count)
            connection_strength[node] = min(strengths) if strengths else 0
    return connection_strength

def filter_graph(G, core_nodes, top_n=25):
    connection_strength = calculate_connection_strength(G, core_nodes)
    top_nodes = sorted(connection_strength, key=connection_strength.get, reverse=True)[:top_n]
    filtered_nodes = set(top_nodes + core_nodes)
    return G.subgraph(filtered_nodes).copy()

def normalize_value(value, min_val, max_val, new_min, new_max):
    if max_val == min_val:
        return new_min
    return ((value - min_val) / (max_val - min_val)) * (new_max - new_min) + new_min

def get_elements(G, timestamp, core_nodes, tapNodeData=None):
    cyto_elements = []
    active_nodes = set(core_nodes)  # Initialize with core nodes

    edge_dict = {}
    edges_up_to_timestamp = []
    interactions_count = {node: 0 for node in G.nodes()}  # Count for all nodes
    
    for edge in G.edges(data=True):
        if edge[2]['timestamp'] <= timestamp:
            source = str(edge[0])
            target = str(edge[1])
            active_nodes.add(source)
            active_nodes.add(target)
            edges_up_to_timestamp.append(edge)
            
            # Count interactions for all nodes
            interactions_count[source] += 1
            interactions_count[target] += 1
            
            if source != target:
                edge_type = edge[2].get('edge_type', 'Unknown')
                key = tuple(sorted((source, target)))  # Ensure consistent ordering
                if key not in edge_dict:
                    edge_dict[key] = {
                        'data': {
                            'source': source,
                            'target': target,
                            'weight': 1,
                            'edge_types': Counter([edge_type]),
                            'edge_to_core': 'false',  # Default value
                            'interactions': {
                                source: Counter([edge_type]),
                                target: Counter()
                            }
                        }
                    }
                else:
                    edge_dict[key]['data']['weight'] += 1
                    edge_dict[key]['data']['edge_types'][edge_type] += 1
                    edge_dict[key]['data']['interactions'][source][edge_type] += 1

    # Normalize edge weights and increase thickness for relationships with lots of interactions
    if edge_dict:
        max_weight = max(edge['data']['weight'] for edge in edge_dict.values())
        for edge in edge_dict.values():
            normalized_weight = normalize_value(
                edge['data']['weight'], 1, max_weight, 1.5, 15
            )  # Increased max thickness by 2x
            edge['data']['normalized_weight'] = normalized_weight

    # Build a temporary graph up to the current timestamp
    temp_G = nx.Graph()
    temp_G.add_nodes_from(active_nodes)
    temp_G.add_edges_from([(e[0], e[1]) for e in edges_up_to_timestamp])

    # Calculate connection strength for non-core nodes
    connection_strength = {}
    for node in temp_G.nodes():
        if node not in core_nodes:
            strengths = []
            for core_node in core_nodes:
                if temp_G.has_edge(node, core_node):
                    edge_count = temp_G.number_of_edges(node, core_node)
                    strengths.append(edge_count)
                else:
                    strengths.append(0)
            connection_strength[node] = min(strengths) if strengths else 0

    # Sort non-core nodes by their connection strength to core nodes
    sorted_nodes = sorted(connection_strength, key=connection_strength.get, reverse=True)

    # Get all timestamps and sort them
    all_timestamps = sorted([edge[2]['timestamp'] for edge in G.edges(data=True)])
    min_timestamp, max_timestamp = min(all_timestamps), max(all_timestamps)

    # Determine N based on timestamp
    N = min(int(normalize_value(timestamp, min_timestamp, max_timestamp, 1, 10)), 10)
    top_N_nodes = sorted_nodes[:N]

    # Mark edges connected to top N non-core nodes
    for edge_key, edge in edge_dict.items():
        source = edge['data']['source']
        target = edge['data']['target']
        if (source in top_N_nodes and target in core_nodes) or (
            target in top_N_nodes and source in core_nodes
        ):
            edge['data']['edge_to_core'] = 'true'
        else:
            edge['data']['edge_to_core'] = 'false'

    # Calculate node metrics for non-core nodes
    centrality = nx.degree_centrality(temp_G)
    betweenness = nx.betweenness_centrality(temp_G)
    max_centrality = max(centrality.values()) if centrality else 1
    max_betweenness = max(betweenness.values()) if betweenness else 1

    # Find the maximum interaction count for normalization
    max_interactions = max(interactions_count.values()) if interactions_count else 1

    for node in active_nodes:
        data = G.nodes[node]
        is_core = node in core_nodes

        # Calculate the number of core nodes this node is connected to
        connected_core_nodes = sum(
            1 for core_node in core_nodes if temp_G.has_edge(node, core_node)
        )

        # Size nodes based on interactions
        base_size = 45  # Base size for all nodes
        size_multiplier = 1 + (interactions_count[node] / max_interactions)  # Normalize size based on interactions
        node_size = base_size * size_multiplier

        # Color nodes
        if is_core:
            node_color = "rgb(0, 255, 0)"  # Green color for core nodes
        else:
            # Color non-core nodes based on betweenness centrality
            if max_betweenness > 0:
                node_color = f"rgb({int(255 * betweenness.get(node, 0) / max_betweenness)}, 0, 255)"
            else:
                node_color = "rgb(0, 0, 255)"  # Default color if max_betweenness is 0


        cyto_elements.append(
            {
                'data': {
                    'id': node,
                    'label': data.get('username', node),
                    'size': node_size,
                    'fid': node,
                    'display_name': data.get('username', 'N/A'),
                    'follower_count': data.get('follower_count', 0),
                    'following_count': data.get('following_count', 0),
                    'is_core': 'true' if is_core else 'false',
                    'centrality': centrality.get(node, 0) if not is_core else 'N/A',
                    'betweenness': betweenness.get(node, 0) if not is_core else 'N/A',
                    'color': node_color,
                    'connected_core_nodes': connected_core_nodes,
                    'interactions_count': interactions_count[node],
                    'pfp_url': data.get('pfp_url')
                }
            }
        )    # Only include edges if it's not the initial stage (timestamp > min_timestamp)
    if timestamp > min_timestamp:
        cyto_elements.extend(list(edge_dict.values()))

    # If a node is selected, highlight paths to core nodes
    if tapNodeData:
        selected_node_id = tapNodeData['id']
        highlighted_edges = set()
        highlighted_nodes = set()
        for core_node in core_nodes:
            try:
                path = nx.shortest_path(temp_G, source=selected_node_id, target=core_node)
                highlighted_nodes.update(path)
                path_edges = list(zip(path[:-1], path[1:]))
                highlighted_edges.update(path_edges)
            except nx.NetworkXNoPath:
                pass  # If no path exists, skip

        # Update elements for highlighting
        for element in cyto_elements:
            data = element['data']
            if 'source' in data and 'target' in data:  # It's an edge
                source = data['source']
                target = data['target']
                if (source, target) in highlighted_edges or (target, source) in highlighted_edges:
                    data['edge_to_core'] = 'true'
                else:
                    data['edge_to_core'] = 'false'
            else:  # It's a node
                node_id = data['id']
                if node_id in highlighted_nodes:
                    data['node_to_core'] = 'true'
                else:
                    data['node_to_core'] = 'false'

    # If it's the initial timestamp (min_timestamp), only show core nodes
    if timestamp <= min_timestamp:
        cyto_elements = [
            element for element in cyto_elements
            if element['data'].get('is_core') == 'true'
        ]

    return cyto_elements