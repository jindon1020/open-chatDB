import re
import requests
from config import Config

SYSTEM_PROMPT_TEMPLATE = """You are a database assistant. The user will ask questions about a database and you should generate appropriate queries.

Current database schema:
{schema}

Database type: {db_type}

Rules:
- For MySQL, generate SQL queries.
- For MongoDB, generate JSON query objects with keys: collection, method, filter, etc.
- For Elasticsearch, generate JSON query objects with keys: index, body, method.
- Always wrap generated queries in a code block with the appropriate language tag (```sql, ```json).
- If the user asks a question that doesn't require a query, just answer it directly.
- Be concise in your explanations.
"""

WRITE_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

MONGO_WRITE_METHODS = {"insertOne", "insertMany", "updateOne", "updateMany", "deleteOne", "deleteMany"}


def resolve_references(text: str, schemas: list[dict]) -> str:
    """Expand @table and #field references to full names for clarity."""
    table_names = {s["table"] for s in schemas}
    field_map: dict[str, str] = {}
    for s in schemas:
        for col in s.get("columns", []):
            fname = col.get("Field", "")
            field_map[fname] = s["table"]

    # @table -> table
    for t in table_names:
        text = text.replace(f"@{t}", t)

    # #field -> table.field
    for f, t in field_map.items():
        text = text.replace(f"#{f}", f"{t}.{f}")

    return text


def extract_code_blocks(text: str) -> list[dict]:
    """Extract fenced code blocks from LLM response."""
    pattern = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
    results = []
    for m in pattern.finditer(text):
        lang = m.group(1).lower()
        code = m.group(2).strip()
        results.append({"lang": lang, "code": code})
    return results


def is_write_operation(query: str, db_type: str = "mysql") -> bool:
    if db_type == "mysql":
        return bool(WRITE_PATTERNS.search(query))
    elif db_type == "mongodb":
        import json
        try:
            q = json.loads(query)
            return q.get("method", "find") in MONGO_WRITE_METHODS
        except Exception:
            return False
    elif db_type == "elasticsearch":
        import json
        try:
            q = json.loads(query)
            return q.get("method", "search") in ("index", "delete", "update")
        except Exception:
            return False
    return False


def chat(messages: list[dict], schema_text: str, db_type: str) -> dict:
    """Call LLM API (OpenAI-compatible) and return assistant response."""
    system_msg = SYSTEM_PROMPT_TEMPLATE.format(schema=schema_text, db_type=db_type)
    api_messages = [{"role": "system", "content": system_msg}] + messages

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {Config.LLM_API_KEY}",
    }
    payload = {
        "model": Config.LLM_MODEL,
        "messages": api_messages,
        "max_tokens": Config.LLM_MAX_TOKENS,
        "temperature": Config.LLM_TEMPERATURE,
    }

    resp = requests.post(
        f"{Config.LLM_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]

    # Extract query blocks
    blocks = extract_code_blocks(content)
    query = None
    query_lang = None
    is_write = False
    if blocks:
        query = blocks[0]["code"]
        query_lang = blocks[0]["lang"]
        is_write = is_write_operation(query, db_type)

    return {
        "content": content,
        "query": query,
        "query_lang": query_lang,
        "is_write": is_write,
    }
