import pickle
import networkx as nx

class GraphRetriever:
    def __init__(self, graph_path):
        """
        Initializes the retriever by loading the knowledge graph.
        """
        self.graph = self.load_graph(graph_path)
        if self.graph is None:
            raise FileNotFoundError(f"Graph file not found at {graph_path}")

    def load_graph(self, path):
        """
        Loads a pickled NetworkX graph object.
        """
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return None

    def find_entities_in_query(self, query):
        """
        A simple method to find entities mentioned in the query by name.
        """
        found_entities = []
        query_lower = query.lower()
        for node, data in self.graph.nodes(data=True):
            # Check if 'name' exists before trying to access it
            if 'name' in data and data['name'].lower() in query_lower:
                found_entities.append(node)
        return found_entities

    def retrieve(self, query, depth=1):
        """
        Retrieves facts from the graph related to the query.
        This version now retrieves node attributes and detailed edge context.
        """
        seed_entities = self.find_entities_in_query(query)
        if not seed_entities:
            return "Could not find any relevant entities in the query."

        facts = set()
        for entity_id in seed_entities:
            # 1. Retrieve the node's own attributes
            node_data = self.graph.nodes[entity_id]
            entity_name = node_data.get('name', entity_id)
            for key, value in node_data.items():
                # Add attributes as facts, skipping basic identifiers
                if key not in ['id', 'name', 'type']:
                    facts.add(f"The '{entity_name}' has attribute '{key}': {value}.")

            # 2. Retrieve facts from the neighborhood (edges and connected nodes)
            neighbors = nx.ego_graph(self.graph, entity_id, radius=depth)
            for u, v, data in neighbors.edges(data=True):
                source_name = self.graph.nodes[u].get('name', u)
                target_name = self.graph.nodes[v].get('name', v)
                
                # Build a more descriptive fact using all available edge data
                relation_label = data.get('label', 'is related to')
                fact = f"{source_name} --[{relation_label}]--> {target_name}."
                
                context = []
                if 'turn' in data and data['turn'] in self.graph.nodes:
                    turn_name = self.graph.nodes[data['turn']].get('name', data['turn'])
                    context.append(f"Turn: {turn_name}")
                if 'context' in data:
                    context.append(f"Context: {data['context']}")
                
                if context:
                    fact += f" ({'; '.join(context)})"
                
                facts.add(fact)
        
        if not facts:
            entity_name = self.graph.nodes[seed_entities[0]].get('name', seed_entities[0])
            return f"Found entity '{entity_name}', but no specific attributes or relationships to report."

        return "\n".join(sorted(list(facts)))

def main():
    """
    Main function to test the updated GraphRetriever.
    """
    game_id = "chs-850-0001"
    graph_filename = f"{game_id}.graph"
    
    try:
        retriever = GraphRetriever(graph_path=graph_filename)

        print("\n--- Testing Retriever ---")
        
        query1 = "white"
        print(f"\nQuery: '{query1}'")
        answer1 = retriever.retrieve(query1)
        print("Answer:")
        print(answer1)

        query2 = "black"
        print(f"\nQuery: '{query2}'")
        answer2 = retriever.retrieve(query2)
        print("Answer:")
        print(answer2)

    except FileNotFoundError:
        print(f"Error: The graph file '{graph_filename}' was not found. Please run the data pipeline first.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()

