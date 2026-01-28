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
- IMPORTANT: Each response must contain AT MOST ONE fenced code block (```sql or ```json), which is the final executable query. Do NOT include multiple code blocks. If you need to reference SQL fragments or examples in your explanation, write them inline without fencing. The single code block will be used as the executable query.
- If the user asks a question that doesn't require a query, just answer it directly without any code block.
- Be concise in your explanations.
- IMPORTANT: When the user's question is ambiguous and cannot be confidently mapped to the schema — for example, the user mentions a business concept like "ongoing", "active", "pending", etc., but there is no column or comment in the schema that clearly corresponds to it — do NOT guess or assume a mapping. Instead, ask the user to clarify which column or value represents the concept they are referring to. You may list the potentially relevant columns and their types to help the user decide. Only generate a query when you are confident about the mapping.
- Always respond with explanations in Chinese. Query code itself remains in its original language (SQL/JSON), but all surrounding text, descriptions, and clarification questions must be in Chinese.
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


EXECUTABLE_SQL_PATTERN = re.compile(
    r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|REPLACE|"
    r"WITH|EXPLAIN|SHOW|DESCRIBE|DESC|USE|SET|GRANT|REVOKE|BEGIN|COMMIT|"
    r"ROLLBACK|CALL|EXECUTE|EXEC|MERGE)\b",
    re.IGNORECASE,
)


def is_executable_query(code: str, lang: str, db_type: str) -> bool:
    """Check whether a code block looks like an executable query."""
    if not code or not code.strip():
        return False
    if db_type in ("mongodb", "elasticsearch"):
        # JSON-based queries — must be valid JSON object or array
        stripped = code.strip()
        return (stripped.startswith("{") and stripped.endswith("}")) or \
               (stripped.startswith("[") and stripped.endswith("]"))
    # SQL-based: must start with a known statement keyword
    return bool(EXECUTABLE_SQL_PATTERN.match(code.strip()))


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


def _api_url(path: str) -> str:
    """Build full API URL, stripping duplicate slashes."""
    base = Config.LLM_BASE_URL.rstrip("/")
    return f"{base}{path}"


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
        _api_url("/chat/completions"),
        headers=headers,
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]

    # Extract query blocks — use last block only if it's executable
    blocks = extract_code_blocks(content)
    query = None
    query_lang = None
    is_write = False
    if blocks:
        candidate = blocks[-1]
        if is_executable_query(candidate["code"], candidate["lang"], db_type):
            query = candidate["code"]
            query_lang = candidate["lang"]
            is_write = is_write_operation(query, db_type)

    return {
        "content": content,
        "query": query,
        "query_lang": query_lang,
        "is_write": is_write,
    }


def chat_stream(messages: list[dict], schema_text: str, db_type: str):
    """Streaming version of chat(). Yields SSE-formatted lines."""
    import json as _json

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
        "stream": True,
    }

    full_content = ""

    try:
        resp = requests.post(
            _api_url("/chat/completions"),
            headers=headers,
            json=payload,
            timeout=120,
            stream=True,
        )
        resp.raise_for_status()

        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            if not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str.strip() == "[DONE]":
                break
            try:
                chunk = _json.loads(data_str)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                token = delta.get("content", "")
                if token:
                    full_content += token
                    yield f"data: {_json.dumps({'type': 'token', 'content': token})}\n\n"
            except (_json.JSONDecodeError, IndexError, KeyError):
                continue

        # Stream finished — use last block only if it's executable
        blocks = extract_code_blocks(full_content)
        query = None
        query_lang = None
        is_write = False
        if blocks:
            candidate = blocks[-1]
            if is_executable_query(candidate["code"], candidate["lang"], db_type):
                query = candidate["code"]
                query_lang = candidate["lang"]
                is_write = is_write_operation(query, db_type)

        done_payload = {
            "type": "done",
            "content": full_content,
            "query": query,
            "query_lang": query_lang,
            "is_write": is_write,
        }
        yield f"data: {_json.dumps(done_payload)}\n\n"

    except Exception as e:
        yield f"data: {_json.dumps({'type': 'error', 'content': str(e)})}\n\n"
