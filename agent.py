#!/usr/bin/env python3
"""
Agent module for answering questions.
"""

import os
import json
import sys
import requests
from dotenv import load_dotenv

load_dotenv('.env.agent.secret')

class Agent:
    def __init__(self):
        self.api_base = os.getenv('LLM_API_BASE', 'http://localhost:8000/v1')
        self.model = os.getenv('LLM_MODEL', 'qwen3-coder-plus')
    
    def call_llm(self, prompt):
        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return f"Error: {response.status_code}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def format_response(self, answer):
        return json.dumps({"answer": answer, "tool_calls": []})

def main():
    if len(sys.argv) < 2:
        print("Usage: python agent.py 'question'")
        sys.exit(1)
    
    agent = Agent()
    answer = agent.call_llm(sys.argv[1])
    print(agent.format_response(answer))

if __name__ == "__main__":
    main()
