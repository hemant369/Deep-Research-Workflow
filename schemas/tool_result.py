from dataclasses import dataclass, field

@dataclass
class ToolResult:
    source: str
    title: str
    content: str
    url: str 
    metadata: dict = field(
        default_factory=dict
    )

