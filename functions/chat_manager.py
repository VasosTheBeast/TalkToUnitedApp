# functions/chat_manager.py
from google import genai
from google.genai import types

class ChatManager:
    def __init__(self, api_key: str, system_prompt: str, model="gemini-2.0-flash-001", keep_history=True):
        self.client = genai.Client(api_key=api_key)
        self.system_prompt = system_prompt
        self.model = model
        self.keep_history = keep_history
        self.messages = []  # conversation history

        # Configuration for the model
        self.config = types.GenerateContentConfig(
            system_instruction=self.system_prompt
        )

    def add_message(self, role: str, text: str):
        """Adds a message to the chat history."""
        msg = types.Content(role=role, parts=[types.Part(text=text)])
        self.messages.append(msg)

        # If we don’t want history, only keep the latest user message
        if not self.keep_history and role == "user":
            self.messages = [msg]

    def ask(self, prompt: str):
        """Send the user's prompt to Gemini and return the model's response."""
        self.add_message("user", prompt)

        response = self.client.models.generate_content(
            model=self.model,
            contents=self.messages,
            config=self.config
        )

        if response is None or not response.candidates:
            return "⚠️ No valid response from model."

        reply_text = response.candidates[0].content.parts[0].text

        # Add the assistant’s reply to history
        self.add_message("assistant", reply_text)
        return reply_text

    def add_dynamic_system_prompt(self, new_instruction: str):
        """Updates the system instruction dynamically."""
        self.system_prompt += "\n" + new_instruction
        self.config = types.GenerateContentConfig(system_instruction=self.system_prompt)
