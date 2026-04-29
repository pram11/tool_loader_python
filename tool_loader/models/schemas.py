from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ToolType(str, Enum):
    MCP = "mcp"
    PYTHON = "python"


class TerminationPolicy(str, Enum):
    PERSISTENT = "PERSISTENT"
    ON_DEMAND = "ON_DEMAND"


class ToolSchema(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., min_length=1)
    type: ToolType
    path_or_cmd: str = Field(..., min_length=1)
    args: List[str] = Field(default_factory=list)
    env_vars: Dict[str, str] = Field(default_factory=dict)
    is_enabled: bool = True
    is_system: bool = False
    termination_policy: TerminationPolicy = TerminationPolicy.ON_DEMAND
    description: str = ""

    model_config = {"use_enum_values": True}
