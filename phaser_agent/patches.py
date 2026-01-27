import json
import logging
from typing import List, Any
from google.genai import types
from google.adk.models import lite_llm
from google.adk.models.llm_response import LlmResponse

logger = logging.getLogger("google.adk.models.lite_llm")

def _patched_message_to_generate_content_response(
    message: Any,
    is_partial: bool = False,
    model_version: str = "",
    thought_parts: List[types.Part] | None = None,
) -> LlmResponse:
  """Converts a litellm message to LlmResponse.
  
  PATCHED: Handles list-wrapped arguments from DeepSeek/other models.
  """
  lite_llm._ensure_litellm_imported()

  parts: List[types.Part] = []
  if not thought_parts:
    thought_parts = lite_llm._convert_reasoning_value_to_parts(
        lite_llm._extract_reasoning_value(message)
    )
  if thought_parts:
    parts.extend(thought_parts)
  
  message_content, tool_calls = lite_llm._split_message_content_and_tool_calls(message)
  if isinstance(message_content, str) and message_content:
    parts.append(types.Part.from_text(text=message_content))

  if tool_calls:
    for tool_call in tool_calls:
      if tool_call.type == "function":
        raw_args = tool_call.function.arguments or "{}"
        try:
            args = json.loads(raw_args)
        except json.JSONDecodeError:
            # Handle potential incomplete JSON or bad formatting from some models
            logger.warning(
                f"Failed to parse arguments for tool {tool_call.function.name}. Attempting repair."
            )
            try:
                import json_repair
                args = json_repair.loads(raw_args)
                logger.info(f"Successfully repaired arguments for tool {tool_call.function.name}")
            except ImportError:
                logger.warning("json_repair not installed. Falling back to empty dict.")
                args = {}
            except Exception as e:
                logger.error(f"Failed to repair JSON: {e}")
                args = {}
        
        # --- PATCH: Unwrap list args ---
        if isinstance(args, list):
            logger.warning(f"Tool arguments for {tool_call.function.name} is a list. Attempting to unwrap.")
            if len(args) > 0 and isinstance(args[0], dict):
                args = args[0]
                logger.info(f"Unwrapped arguments: {args}")
            else:
                logger.error(f"Could not unwrap list args: {args}. using empty dict.")
                args = {}
        # -----------------------------
        
        part = types.Part.from_function_call(
            name=tool_call.function.name,
            args=args,
        )
        part.function_call.id = tool_call.id
        parts.append(part)

  return LlmResponse(
      content=types.Content(role="model", parts=parts),
      partial=is_partial,
      model_version=model_version,
  )

def apply_patches():
    """Applies monkeypatches to fix library issues."""
    logger.info("Applying LiteLLM monkeypatch for list-wrapped tool arguments.")
    lite_llm._message_to_generate_content_response = _patched_message_to_generate_content_response
