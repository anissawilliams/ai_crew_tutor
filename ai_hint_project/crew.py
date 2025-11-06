import os
import sys
import re
import yaml
import streamlit as st
from crewai import Crew, Agent, Task
from ai_hint_project.tools.rag_tool import build_rag_tool
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEndpoint
import requests
from . import levels

print("✅ crew.py loaded")

# 🔧 Base paths
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)

# Retrieve the Hugging Face Access Token from Streamlit secrets
HF_ACCESS_TOKEN = st.secrets["HUGGINGFACE_ACCESS_TOKEN"]


def get_llm():
    """Create a proper LangChain LLM instance for CrewAI"""
    try:
        print("🔌 Creating Hugging Face LLM...")

        # Use HuggingFaceEndpoint for proper LangChain integration
        llm = HuggingFaceEndpoint(
            repo_id="gpt2",  # or "mistralai/Mistral-7B-v0.1" for better results
            huggingfacehub_api_token=HF_ACCESS_TOKEN,
            max_length=512,
            temperature=0.7,
        )

        print("✅ Hugging Face LLM successfully created!")
        return llm

    except Exception as e:
        print(f"⚠️ Exception occurred: {e}")
        print("⚠️ Falling back to ChatOpenAI")

        # Fallback to OpenAI if you have that key
        if "OPENAI_API_KEY" in st.secrets:
            return ChatOpenAI(
                model="gpt-3.5-turbo",
                api_key=st.secrets["OPENAI_API_KEY"],
                temperature=0.7
            )

        # Last resort: fake LLM for testing
        from langchain_community.llms.fake import FakeListLLM
        return FakeListLLM(responses=["This is a test response. AI is not properly configured."])


# Rest of your code stays the same...
# (persona_reactions, is_code_input, load_yaml, etc.)

# ✅ Build RAG tool
rag_folder = os.path.join(base_dir, "baeldung_scraper")
rag_tool, _ = build_rag_tool(
    index_path=os.path.join(rag_folder, "baeldung_scraper"),
    chunks_path=os.path.join(rag_folder, "chunks.json")
)

# 🎭 Persona reactions
persona_reactions = {
    "Batman": "Code received. Let's patch the vulnerability.",
    "Yoda": "Code, you have pasted. Analyze it, we must.",
    "Spider-Gwen": "Let's swing through this syntax.",
    "Shuri": "Let's scan it with Wakandan tech.",
    "Elsa": "Let me freeze the bugs and refactor.",
    "Wednesday Addams": "Let's dissect it like a corpse.",
    "Iron Man": "Let's run diagnostics and upgrade it.",
    "Nova": "Let's orbit through its logic.",
    "Zee": "Let's treat this like a boss fight.",
    "Sherlock Holmes": "Let's deduce its structure."
}


# 🧠 Detect code input
def is_code_input(text):
    code_patterns = [
        r"\bdef\b", r"\bclass\b", r"\bimport\b", r"\breturn\b",
        r"\bif\b\s*\(?.*?\)?\s*:", r"\bfor\b\s*\(?.*?\)?\s*:", r"\bwhile\b\s*\(?.*?\)?\s*:",
        r"\btry\b\s*:", r"\bexcept\b\s*:", r"\w+\s*=\s*.+", r"\w+\(.*?\)", r"{.*?}", r"<.*?>"
    ]
    return any(re.search(pattern, text) for pattern in code_patterns)


# 📦 Load YAML
def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


# 🚀 Crew creation
def create_crew(persona: str, user_question: str):
    print(f"✅ create_crew() called with persona: {persona}")

    base_dir = os.path.dirname(__file__)
    agents_config = load_yaml(os.path.join(base_dir, 'config/agents.yaml'))
    tasks_config = load_yaml(os.path.join(base_dir, 'config/tasks.yaml'))

    agent_cfg = agents_config['agents'].get(persona)
    if not agent_cfg:
        raise ValueError(f"Unknown persona: {persona}")

    # Get the LLM instance (now properly created)
    llm = get_llm()
    print("✅ LLM type:", type(llm))

    agent = Agent(
        role=agent_cfg["role"],
        goal=agent_cfg["goal"],
        backstory=agent_cfg["backstory"],
        level=agent_cfg.get("level", "beginner"),
        verbose=False,
        llm=llm
    )

    reaction = persona_reactions.get(persona, "No reaction available.")
    task_description = f"{reaction}\n\n{user_question}" if is_code_input(user_question) else user_question

    context = rag_tool(user_question)

    task_template = tasks_config['tasks']['explainer']
    task = Task(
        name=task_template['name'],
        description=task_template['description'].format(query=f"{task_description}\n\nRelevant context:\n{context}"),
        expected_output=task_template['expected_output'],
        agent=agent
    )

    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    result = crew.kickoff()

    levels.update_level(persona)

    cleaned_content = re.sub(r"<think>.*?</think>\n?", "", result.tasks_output[0].raw, flags=re.DOTALL)

    return cleaned_content