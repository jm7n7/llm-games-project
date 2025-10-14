import json
import networkx as nx
import matplotlib.pyplot as plt
import pickle

def build_knowledge_graph(graph_data):
    """
    Builds a NetworkX graph from the extracted entities and relations.
    This version is updated to handle the new JSON structure with "subject", 
    "object", and additional edge attributes.
    """
    G = nx.DiGraph()

    # Add nodes (entities) with all their data as attributes
    for entity in graph_data.get('entities', []):
        node_id = entity['id']
        node_attributes = {k: v for k, v in entity.items() if k != 'id'}
        G.add_node(node_id, **node_attributes)
        
    # Add edges (relations) using the new "subject" and "object" keys
    for relation in graph_data.get('relations', []):
        subject_id = relation.get('subject')
        object_id = relation.get('object')
        
        # Ensure both subject and object nodes exist before adding an edge
        if G.has_node(subject_id) and G.has_node(object_id):
            # Use the 'relationship' key for the label for visualization
            edge_attributes = {
                'label': relation.get('relationship'),
                'turn': relation.get('turn'),
                'context': relation.get('context')
            }
            # Add the edge with all available data as attributes
            G.add_edge(subject_id, object_id, **edge_attributes)
        
    return G

def visualize_graph(G, game_id):
    """
    Creates and saves a visualization of the knowledge graph.
    """
    plt.figure(figsize=(22, 22))
    
    pos = nx.spring_layout(G, k=1.0, iterations=50)

    nx.draw_networkx_nodes(G, pos, node_size=2500, node_color='skyblue', alpha=0.9)
    nx.draw_networkx_edges(G, pos, edgelist=G.edges(), edge_color='gray', arrows=True, arrowstyle='->', arrowsize=20)
    
    labels = {node: data.get('name', 'N/A') for node, data in G.nodes(data=True)}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=9, font_weight='bold')
    
    edge_labels = nx.get_edge_attributes(G, 'label')
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='darkred', font_size=8)

    plt.title(f"Knowledge Graph for Game: {game_id}", size=24)
    plt.axis('off')
    
    output_filename = f"{game_id}_knowledge_graph.png"
    plt.savefig(output_filename, format="PNG", bbox_inches='tight')
    print(f"Successfully saved graph visualization to {output_filename}")
    plt.close()

def main():
    """
    Main function to load data, build the graph, visualize, and save it.
    """
    game_id = "chs-850-0001"
    json_input_filename = f"{game_id}_graph_data.json"
    graph_output_filename = f"{game_id}.graph"

    try:
        with open(json_input_filename, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        
        print(f"Successfully loaded graph data from {json_input_filename}")
        
        print("Building knowledge graph...")
        knowledge_graph = build_knowledge_graph(graph_data)
        
        print(f"Graph built with {knowledge_graph.number_of_nodes()} nodes and {knowledge_graph.number_of_edges()} edges.")
        
        print("Saving graph object...")
        with open(graph_output_filename, 'wb') as f:
            pickle.dump(knowledge_graph, f)
        print(f"Successfully saved graph object to {graph_output_filename}")

        print("Generating graph visualization...")
        visualize_graph(knowledge_graph, game_id)
        
    except FileNotFoundError:
        print(f"Error: The graph data file '{json_input_filename}' was not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()