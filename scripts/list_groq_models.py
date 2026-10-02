# scripts/list_groq_models.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from groq import Groq
from src.config import GROQ_API_KEY

for m in Groq(api_key=GROQ_API_KEY).models.list().data:
    print(m.id)