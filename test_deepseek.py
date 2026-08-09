import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

print("Sending test request to DeepSeek...")

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role": "user", "content": "Reply with exactly this JSON: {\"status\": \"ok\"}"}],
    temperature=0,
    max_tokens=50
)

content = response.choices[0].message.content
print("API Response:")
print(content)