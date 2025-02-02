from abc import ABC, abstractmethod
import re
from typing import Dict, List, Optional

from pythmata.core.engine.token import Token
from pythmata.core.state import StateManager

class Gateway(ABC):
    """Base class for BPMN gateways."""
    
    def __init__(self, gateway_id: str, state_manager: StateManager):
        self.id = gateway_id
        self.state_manager = state_manager

    @abstractmethod
    async def select_path(self, token: Token, flows: Dict) -> str:
        """Select outgoing path based on gateway type and conditions."""
        pass

class ExclusiveGateway(Gateway):
    """
    Implementation of BPMN Exclusive Gateway (XOR).
    
    Selects exactly one outgoing path based on conditions. If no conditions
    match, selects the default path if available.
    """
    
    async def evaluate_condition(self, token: Token, condition: Optional[str]) -> bool:
        """
        Evaluate a condition expression using token data.
        
        Args:
            token: Process token containing variables
            condition: Condition expression (e.g., ${amount > 1000})
            
        Returns:
            True if condition evaluates to true, False otherwise
        """
        if not condition:
            return True  # Default path
            
        # Extract variable references
        var_pattern = r'\${([^}]+)}'
        if not re.match(r'^\${.+}$', condition):
            raise ValueError(f"Invalid condition syntax: {condition}")
            
        expr = condition[2:-1]  # Remove ${ and }
        
        # Convert JavaScript-style operators to Python
        expr = expr.replace('&&', ' and ').replace('||', ' or ')
        
        # Create evaluation environment with token data
        eval_dict = {
            "True": True,
            "False": False,
            "None": None,
            "true": True,
            "false": False,
            **token.data  # Add token variables to environment
        }
        
        try:
            # Evaluate the expression
            return bool(eval(expr, {"__builtins__": {}}, eval_dict))
        except Exception as e:
            print(f"Failed to evaluate expression: {expr}")
            print(f"Error: {e}")
            return False

    async def select_path(self, token: Token, flows: Dict) -> str:
        """
        Select outgoing path based on conditions.
        
        Args:
            token: Process token
            flows: Dict of flow_id -> flow_data with conditions
            
        Returns:
            ID of selected flow
        """
        # First check conditional paths
        for flow_id, flow_data in flows.items():
            condition = flow_data.get("condition")
            if await self.evaluate_condition(token, condition):
                return flow_id
                
        # Find default path (no condition)
        for flow_id, flow_data in flows.items():
            if not flow_data.get("condition"):
                return flow_id
                
        raise ValueError(
            f"No valid path found for gateway {self.id} and no default path defined"
        )

class InclusiveGateway(Gateway):
    """
    Implementation of BPMN Inclusive Gateway (OR).
    
    Selects one or more outgoing paths based on conditions. Multiple paths
    can be activated if their conditions evaluate to true. If no conditions
    match, selects the default path if available.
    """
    
    async def select_path(self, token: Token, flows: Dict) -> str:
        """
        Select a single path (required by Gateway ABC).
        This implementation always returns the first valid path.
        For multiple paths, use select_paths instead.
        """
        paths = await self.select_paths(token, flows)
        return paths[0]

    async def evaluate_condition(self, token: Token, condition: Optional[str]) -> bool:
        """
        Evaluate a condition expression using token data.
        
        Args:
            token: Process token containing variables
            condition: Condition expression (e.g., ${amount > 1000})
            
        Returns:
            True if condition evaluates to true, False otherwise
        """
        if not condition:
            return True  # Default path
            
        # Extract variable references
        var_pattern = r'\${([^}]+)}'
        if not re.match(r'^\${.+}$', condition):
            raise ValueError(f"Invalid condition syntax: {condition}")
            
        expr = condition[2:-1]  # Remove ${ and }
        
        # Convert JavaScript-style operators to Python
        expr = expr.replace('&&', ' and ').replace('||', ' or ')
        
        # Create evaluation environment with token data
        eval_dict = {
            "True": True,
            "False": False,
            "None": None,
            "true": True,
            "false": False,
            **token.data  # Add token variables to environment
        }
        
        try:
            # Evaluate the expression
            return bool(eval(expr, {"__builtins__": {}}, eval_dict))
        except Exception as e:
            print(f"Failed to evaluate expression: {expr}")
            print(f"Error: {e}")
            return False

    async def select_paths(self, token: Token, flows: Dict) -> List[str]:
        """
        Select all outgoing paths with conditions that evaluate to true.
        
        Args:
            token: Process token
            flows: Dict of flow_id -> flow_data with conditions
            
        Returns:
            List of selected flow IDs
        """
        selected_flows = []
        has_matching_condition = False
        default_flow = None
        
        # First check all conditional paths
        for flow_id, flow_data in flows.items():
            condition = flow_data.get("condition")
            if condition is None:
                default_flow = flow_id
                continue
                
            if await self.evaluate_condition(token, condition):
                selected_flows.append(flow_id)
                has_matching_condition = True
                
        # If no conditions matched and there's a default path, use it
        if not has_matching_condition and default_flow:
            return [default_flow]
            
        # If no conditions matched and no default path, raise error
        if not selected_flows:
            raise ValueError(
                f"No valid paths found for gateway {self.id} and no default path defined"
            )
            
        return selected_flows
