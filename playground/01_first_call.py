from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()                      # reads OPENAI_API_KEY from .env
client = OpenAI()
MODEL = "gpt-4o-mini"              # cheap model for practice

# 1) plain text
r = client.responses.create(model=MODEL,
        instructions="Answer in one sentence.",
        input="What is RAG?")
print(r.output_text)

# 2) structured output: the model MUST return this shape
class Enrichment(BaseModel):
    summary: str
    tags: list[str]

r = client.responses.parse(model=MODEL,
        instructions="Summarize in 1-2 sentences and give 3-5 tags.",
        input="OpenAI released a new small model that is cheaper and faster...",
        text_format=Enrichment)
print(r.output_parsed)             # Enrichment(summary=..., tags=[...])