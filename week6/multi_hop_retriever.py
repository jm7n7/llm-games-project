import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from graph_retriever import GraphRetriever

# --- Configuration ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("GOOGLE_API_KEY not found. Please ensure your .env file is set up correctly.")

genai.configure(api_key=API_KEY)
llm = genai.GenerativeModel('gemini-2.5-flash')

class MultiHopRetriever:
    def __init__(self, graph_retriever):
        """
        Initializes the multi-hop retriever with a graph retriever instance.
        """
        self.graph_retriever = graph_retriever

    def decompose_query(self, original_query):
        """
        Uses an LLM to break a complex query into a list of simple, self-contained questions.
        """
        prompt = f"""
        Given the user's query, break it down into a series of simple, self-contained questions 
        that can be answered independently by a knowledge graph.
        
        - Each question should be answerable on its own.
        - If the query is already simple, return an empty list.
        - The goal is to gather facts. Rephrase questions to ask "what," "who," or "which" instead of "is there" or "was it."
        
        User Query: "{original_query}"
        
        Return the result as a JSON object with a single key "sub_questions" which contains a list of strings.
        
        Example 1:
        User Query: "What move lost the game for black and how good was white's d-pawn?"
        JSON Output:
        {{
            "sub_questions": [
                "Which move lost the game for black?",
                "What was the quality of white's d-pawn?"
            ]
        }}
        
        Example 2:
        User Query: "Did white win?"
        JSON Output:
        {{
            "sub_questions": []
        }}
        
        JSON Output:
        """
        
        response = llm.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        
        try:
            data = json.loads(cleaned_response)
            return data.get("sub_questions", [])
        except json.JSONDecodeError:
            return [] # Return empty list if JSON is invalid

    def synthesize_answer(self, original_query, evidence_list):
        """
        Uses an LLM to synthesize a final answer from the collected evidence.
        """
        evidence_str = "\n\n".join(evidence_list)
        prompt = f"""
        Based on the following evidence gathered from a knowledge graph, provide a concise, 
        well-formulated answer to the user's original query.
        
        Do not just repeat the evidence. Synthesize it into a natural, human-readable paragraph.
        
        Original Query: "{original_query}"
        
        Evidence:
        ---
        {evidence_str}
        ---
        
        Final Answer:
        """
        response = llm.generate_content(prompt)
        return response.text

    def retrieve(self, original_query):
        """
        Orchestrates the full multi-hop retrieval and synthesis process.
        This version now correctly synthesizes answers for simple queries too.
        """
        sub_questions = self.decompose_query(original_query)
        
        evidence_list = []
        reasoning_trace = []

        # If there are sub-questions, handle the multi-hop logic
        if sub_questions:
            for i, sub_q in enumerate(sub_questions):
                print(f"\nHop {i+1}: Answering sub-question: '{sub_q}'")
                evidence = self.graph_retriever.retrieve(sub_q)
                evidence_list.append(evidence)
                reasoning_trace.append(f"  Q: {sub_q}\n  A: {evidence}")
                print(f"Evidence: {evidence}")
            
            final_answer = self.synthesize_answer(original_query, evidence_list)
        
        # Logic for simple queries: retrieve evidence AND then synthesize
        else:
            evidence = self.graph_retriever.retrieve(original_query)
            if "Could not find" in evidence:
                final_answer = "I could not find an answer to your question in the provided game analysis."
                reasoning_trace.append("No relevant entities found for direct retrieval.")
            else:
                # Crucially, we now synthesize even for simple queries
                final_answer = self.synthesize_answer(original_query, [evidence])
                reasoning_trace.append(f"Direct retrieval evidence:\n{evidence}")

        return final_answer, "\n".join(reasoning_trace)

def main():
    """
    Main function to test the MultiHopRetriever.
    """
    game_id = "chs-850-0001"
    graph_filename = f"{game_id}.graph"

    try:
        graph_retriever = GraphRetriever(graph_path=graph_filename)
        multi_hop_retriever = MultiHopRetriever(graph_retriever)

        # Test Case 1: A complex, multi-part query
        complex_query = "Which move lost the game for black and how good was white's d-pawn?"
        print(f"--- Starting Multi-Hop Retrieval for: '{complex_query}' ---")
        final_answer, trace = multi_hop_retriever.retrieve(complex_query)
        
        print("\n\n--- Multi-Hop Retrieval Complete ---")
        print(f"\nOriginal Query: {complex_query}")
        print(f"\nFinal Answer: {final_answer}")
        print("\n--- Reasoning Trace ---")
        print(trace)

        # Test Case 2: A simple, single-fact query
        simple_query = "did white win the game?"
        print(f"\n\n--- Starting Retrieval for: '{simple_query}' ---")
        final_answer_simple, trace_simple = multi_hop_retriever.retrieve(simple_query)

        print("\n\n--- Retrieval Complete ---")
        print(f"\nOriginal Query: {simple_query}")
        print(f"\nFinal Answer: {final_answer_simple}")
        print("\n--- Reasoning Trace ---")
        print(trace_simple)

    except FileNotFoundError:
        print(f"Error: Could not find the graph file '{graph_filename}'. Please run the full data pipeline first.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()