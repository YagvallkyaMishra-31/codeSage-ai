"""
Prompt builder for the Debug Assistant.
Constructs structured prompts with error context and retrieved code.
"""


def build_debug_prompt(error_text: str, retrieved_chunks: list[dict], graph_context: dict | None = None) -> list[dict]:
    """
    Build a chat-format prompt for the LLM.

    Args:
        error_text: The error message, stack trace, or code snippet from the user
        retrieved_chunks: List of code chunks from semantic search with
                         keys: file_path, language, chunk, score

    Returns:
        List of message dicts for the OpenAI chat API
    """
    # Format retrieved code context
    if retrieved_chunks:
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            context_parts.append(
                f"--- File: {chunk['file_path']} ({chunk.get('language', 'Unknown')}) "
                f"[Relevance: {chunk.get('score', 0):.2f}] ---\n"
                f"{chunk['chunk']}"
            )
        code_context = "\n\n".join(context_parts)
    else:
        code_context = "No relevant repository code was found."
        
    # Format graph context
    if graph_context:
        graph_parts = []
        for file_path, data in graph_context.items():
            imports = ", ".join(data.get("imports", [])) or "None"
            functions = ", ".join(data.get("functions", [])) or "None"
            calls = ", ".join(data.get("calls", [])) or "None"
            
            graph_parts.append(
                f"- **{file_path}**:\n"
                f"  Imports: {imports}\n"
                f"  Defines: {functions}\n"
                f"  Calls: {calls}"
            )
        graph_text = "\n".join(graph_parts)
    else:
        graph_text = "No dependency graph context available."

    system_message = """You are an expert software debugging assistant analyzing code from a developer's repository. 
You have deep knowledge of programming languages, frameworks, and common bug patterns.
Always provide structured, actionable analysis.
Respond ONLY with valid JSON (no markdown, no code fences)."""

    user_message = f"""## Error / Issue Reported

{error_text}

## Relevant Code from Repository

{code_context}

## Codebase Dependencies & Graph Context
{graph_text}

## Your Task

Analyze the error above using the repository code context. Respond with a JSON object containing exactly these fields:

{{
  "root_cause": "A concise description of what is causing the error",
  "explanation": "A detailed explanation of why this error occurs, referencing specific code",
  "suggested_fix": "Step-by-step instructions to fix the issue",
  "code_patch": "The corrected code snippet that fixes the issue",
  "related_files": ["list", "of", "relevant", "file", "paths"],
  "severity": "low | medium | high | critical",
  "category": "e.g. TypeError, MemoryLeak, RaceCondition, etc."
}}"""

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]
