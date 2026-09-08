import json
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ContextLimits:
    max_system_message_chars: int = 48_000
    max_input_chars: int = 120_000
    max_message_chars: int = 16_000
    max_tool_output_chars: int = 12_000
    min_recent_messages: int = 4
    max_retries: int = 4

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "ContextLimits":
        if not raw:
            return cls()

        values = {
            "max_system_message_chars": int(raw.get("max_system_message_chars", cls.max_system_message_chars)),
            "max_input_chars": int(raw.get("max_input_chars", cls.max_input_chars)),
            "max_message_chars": int(raw.get("max_message_chars", cls.max_message_chars)),
            "max_tool_output_chars": int(raw.get("max_tool_output_chars", cls.max_tool_output_chars)),
            "min_recent_messages": int(raw.get("min_recent_messages", cls.min_recent_messages)),
            "max_retries": int(raw.get("max_retries", cls.max_retries)),
        }

        return cls(**values)


class ContextWindowGuard:
    def __init__(self, limits: ContextLimits):
        self.limits = limits

    @staticmethod
    def _to_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            return str(value)

    @staticmethod
    def _truncate_with_notice(text: str, limit: int) -> str:
        if limit <= 0:
            return ""

        if len(text) <= limit:
            return text

        notice = "\n\n[TRUNCATED: context budget applied]"
        if limit <= len(notice):
            return text[:limit]
        return text[: limit - len(notice)] + notice

    def trim_system_message(self, system_message: str) -> str:
        return self._truncate_with_notice(
            self._to_text(system_message),
            self.limits.max_system_message_chars,
        )

    def trim_tool_output(self, value: Any) -> str:
        return self._truncate_with_notice(
            self._to_text(value),
            self.limits.max_tool_output_chars,
        )

    def _trim_message_content(self, content: Any, attempt: int) -> str:
        factor = max(1, attempt)
        per_message_limit = max(600, self.limits.max_message_chars // factor)
        return self._truncate_with_notice(self._to_text(content), per_message_limit)

    def trim_messages(
        self,
        messages: list[dict[str, Any]],
        attempt: int = 1,
    ) -> list[dict[str, Any]]:
        if not messages:
            return []

        factor = max(1, attempt)
        total_budget = max(2_000, self.limits.max_input_chars // factor)
        min_keep = max(1, self.limits.min_recent_messages)

        selected_reversed: list[dict[str, Any]] = []
        used_chars = 0

        for original in reversed(messages):
            if isinstance(original, dict):
                message = dict(original)
            else:
                role = getattr(original, "role", "assistant")
                content = getattr(original, "content", self._to_text(original))
                message = {
                    "role": role,
                    "content": content,
                }

            if "content" in message:
                message["content"] = self._trim_message_content(message.get("content"), attempt)
            else:
                message["content"] = ""

            content_chars = len(message.get("content") or "")

            if used_chars + content_chars <= total_budget:
                selected_reversed.append(message)
                used_chars += content_chars
                continue

            if len(selected_reversed) < min_keep:
                remaining = max(300, total_budget - used_chars)
                message["content"] = self._truncate_with_notice(message["content"], remaining)
                selected_reversed.append(message)
                used_chars += len(message["content"])
                continue

            break

        ordered_messages = list(reversed(selected_reversed))
        system_messages = [
            message for message in ordered_messages
            if message.get("role") == "system"
        ]
        non_system_messages = [
            message for message in ordered_messages
            if message.get("role") != "system"
        ]
        return [*system_messages, *non_system_messages]

    def trim_response_input_items(
        self,
        items: list[dict[str, Any]],
        attempt: int = 1,
    ) -> list[dict[str, Any]]:
        trimmed = self.trim_messages(items, attempt=attempt)
        sanitized: list[dict[str, Any]] = []

        for item in trimmed:
            role = item.get("role")
            if role not in {"user", "assistant"}:
                continue
            sanitized.append(
                {
                    "role": role,
                    "content": self._to_text(item.get("content")),
                }
            )

        return sanitized

    def trim_function_call_outputs(
        self,
        outputs: list[dict[str, Any]],
        attempt: int = 1,
    ) -> list[dict[str, Any]]:
        if not outputs:
            return []

        factor = max(1, attempt)
        total_budget = max(2_000, self.limits.max_input_chars // factor)
        output_count = max(1, len(outputs))

        # Every function_call requires a matching function_call_output.
        # Never drop outputs; reduce each payload aggressively when needed.
        per_output_limit = min(
            max(64, total_budget // output_count),
            max(64, self.limits.max_tool_output_chars // factor),
        )

        bounded: list[dict[str, Any]] = []

        for output in outputs:
            item = dict(output)
            payload = self._truncate_with_notice(
                self._to_text(item.get("output", "")),
                per_output_limit,
            )

            item["output"] = payload
            bounded.append(item)

        used_chars = sum(len(self._to_text(item.get("output", ""))) for item in bounded)
        if used_chars > total_budget and output_count > 0:
            stricter_limit = max(16, total_budget // output_count)
            for item in bounded:
                item["output"] = self._truncate_with_notice(
                    self._to_text(item.get("output", "")),
                    stricter_limit,
                )

        return bounded

    @staticmethod
    def is_context_length_error(exc: Exception) -> bool:
        error_text = str(exc).lower()
        indicators = (
            "context window",
            "context_length_exceeded",
            "maximum context length",
            "too many tokens",
        )
        if any(token in error_text for token in indicators):
            return True

        code = getattr(exc, "code", None)
        if isinstance(code, str) and code.lower() == "context_length_exceeded":
            return True

        return False