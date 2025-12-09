from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class StrategyMeta:
    """
    Strategy-level metadata describing:
      - name: unique strategy name
      - symbol: instrument symbol (e.g., 'INFY-EQ')
      - params: strategy parameters dict
    """
    name: str
    symbol: str
    params: Dict[str, Any]
