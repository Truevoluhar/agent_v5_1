from dataclasses import dataclass
from typing import Optional, Callable

@dataclass
class ToolResult:
    ok: bool
    output: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None

@dataclass
class Tool:
    name: str
    description: str
    parameters: str
    executor: Callable[..., ToolResult]
    max_output_chars: int = 12_000
    

    def schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "strict": True,
                "parameters": self.parameters
            }
        }