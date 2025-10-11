import os
from dotenv import load_dotenv
import google.generativeai as genai # Corrected import

load_dotenv()


# Load your API key from an environment variable
api_key = os.getenv('GOOGLE_API_KEY')

# It's a good practice to check if the key was found
if not api_key:
    raise ValueError("Error: GOOGLE_API_KEY environment variable not set.")

genai.configure(api_key=api_key)

# Use a current, stable model name
model = genai.GenerativeModel('gemini-2.5-flash')
chat = model.start_chat()

try:
    response = chat.send_message('I have a dog whose name is pickles.')
    print(response.text)

    response = chat.send_message('what is my dogs name?')
    print(response.text)

except Exception as e:
    print(f"An error occurred: {e}")