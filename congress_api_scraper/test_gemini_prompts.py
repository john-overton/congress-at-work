"""
Install the Google AI Python SDK

$ pip install google-generativeai
"""

import os
import google.generativeai as genai
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'keys'))

from keys import gg_key

genai.configure(api_key=gg_key)

#Prompt to use
prompt = """

"""

# Create the model
generation_config = {
  "temperature": 1.00,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
  generation_config=generation_config,
  # safety_settings = Adjust safety settings
  # See https://ai.google.dev/gemini-api/docs/safety-settings
)

response = model.generate_content(prompt)

print(response.text)