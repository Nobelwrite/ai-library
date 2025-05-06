import os
import re
from dotenv import load_dotenv
from typing import List, Dict, Optional, Any # Added Any
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel


# Let's proceed assuming books_data is accessible for now (fix import later)
try:
    from data_store import books_data, inventory, orders
except ImportError:
    print("ERROR in ai_service: Failed to import books_data from app. Using empty data.")
    books_data = {}

# --- Load Environment Variables ---
load_dotenv()
model = GeminiModel('gemini-1.5-flash', provider='google-gla') # Ensure google-gla provider works or remove
api_key_loaded = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')

# --- NEW FUNCTION: get_available_titles ---
def get_available_book_titles() -> List[str]:

    #Retrieves a list of book titles from the books_data.
    #Handles potential errors and ensures a list is always returned.

    try:
        # Make sure books_data is the dictionary {id: {details}}
        if not isinstance(books_data, dict):
             print("ERROR in get_available_titles: books_data is not a dictionary.")
             return [] # Return empty list on structure error

        titles = [
            details['title']
            for details in books_data.values()
            if isinstance(details, dict) and 'title' in details and isinstance(details['title'], str)
        ]
        print(f"DEBUG: get_available_titles returning: {titles}") # Debug print
        return titles
    except Exception as e:
        print(f"ERROR retrieving available titles: {e}")
        return [] # Return empty list on any error

# --- EXISTING FUNCTION: extract_title ---
# Note: Corrected type hint for known_titles from Dict to List[str]
def extract_title(query: str, known_titles: List[str]) -> Optional[str]:
    """Attempts to extract a known book title from the user query."""
    if not isinstance(known_titles, list):
        print(f"ERROR in extract_title: known_titles is not a list ({type(known_titles)})")
        return None # Cannot process if titles aren't a list

    lower_query = query.lower()
    for title in known_titles:
        # Ensure title is a string before calling .lower()
        if isinstance(title, str):
            # print(f"DEBUG: Checking title={repr(title)}, type={type(title)}") # Optional debug
            if title.lower() in lower_query:
                return title # Return the correctly capitalized version
        else:
            print(f"WARNING: Skipping non-string item during title extraction: {repr(title)}")
    print("DEBUG: No known title directly mentioned in query.")
    return None # Return None if no title found

# --- NEW FUNCTION: get_ai_response (Handles Gemini Call) ---
# Moved the agent logic into a function to be called by app.py
def get_ai_response(user_query: str, available_book_titles: List[str]) -> Dict[str, Any]:
    """
    Processes user query using AI. Extracts title, validates,
    calls Gemini if appropriate, or returns refusal/error message.
    """
    if not model or not api_key_loaded:
         return {"error": "AI model not initialized or API key missing."}

    requested_title = extract_title(user_query, available_book_titles)

    if requested_title:
        # Title is in our allowed list
        print(f"\n--- Title '{requested_title}' Found in List ---")
        print("Proceeding to ask LLM to answer the query about this book...")

        system_prompt_answer = f"""
            You are a helpful and knowledgeable literary assistant providing information ONLY about the book "{requested_title}".
            Do not discuss other books. If the user asks about other books or topics not directly related to "{requested_title}", politely refuse.
            Answer the user's query comprehensively using your general knowledge about "{requested_title}".
            """
        answering_agent = Agent(
            model=model,
            output_type=str, # Expecting a string response
            system_prompt=system_prompt_answer
        )
        try:
            # Pass the original user query to the agent
            result = answering_agent.run_sync(user_prompt=user_query)
            print(f"--- LLM Answer for '{requested_title}' ---")
            print(result)
            return {"data": {"response": result, "title_match": requested_title}, "status": "success"}
        except Exception as e:
            print(f"ERROR during agent run for '{requested_title}': {e}")
            return {"error": f"AI agent failed to process the query for '{requested_title}'.", "title_match": requested_title}

    else:
        # Title not found in the list or couldn't be extracted
        print("\n--- Title Not Found in Allowed List or Not Extracted ---")
        potential_title_match = re.search(r'(?:book|about|titled|of)\s+([\'"]?)(.+?)\1(?:$|\?|\.)', user_query, re.IGNORECASE)
        title_mentioned = potential_title_match.group(2).strip() if potential_title_match else "the requested book"

        refusal_message = f"I am sorry, I cannot provide information about '{title_mentioned}' as it is not in my allowed list of books ({', '.join(available_book_titles)})."
        print(refusal_message)
        return {"error": refusal_message, "title_match": None}





















