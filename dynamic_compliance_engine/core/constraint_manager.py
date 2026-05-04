"""
Dynamic Constraint Manager

Manages the lifecycle of solver constraints, supporting dynamic updates
from regulatory changes and real-time portfolio state.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import hashlib


class ConstraintType(Enum):
    """Types of constraints supported by the solver."""
    LINEAR_INEQUALITY = "linear_inequality"
    LINEAR_EQUALITY = "linear_equality"
    BOOLEAN = "boolean"
    INTEGER_BOUNDS = "integer_bounds"
    REAL_BOUNDS = "real_bounds"
    IMPLICATION = "implication"
    CARDINALITY = "cardinality"


class ConstraintSource(Enum):
    """Source of constraint origin."""
    REGULATORY_RULE = "regulatory_rule"
    PORTFOLIO_LIMIT = "portfolio_limit"
    BUSINESS_POLICY = "business_policy"
    CUSTOMER_REQUIREMENT = "customer_requirement"
    SYSTEM_GENERATED = "system_generated"


@dataclass
class ConstraintVariable:
    """Represents a variable in the constraint system."""
    name: str
    var_type: str  # "int", "real", "bool"
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    description: str = ""
    
    def to_smt_lib(self) -> str:
        """Generate SMT-LIB declaration for this variable."""
        if self.var_type == "bool":
            return f"(declare-const {self.name} Bool)"
        elif self.var_type == "int":
            return f"(declare-const {self.name} Int)"
        else:  # real
            return f"(declare-const {self.name} Real)"


@dataclass
class Constraint:
    """
    Represents a single constraint in the system.
    
    Constraints are expressed in a solver-agnostic format that can be
    translated to various backend solvers (Z3, CVC5, etc.).
    """
    constraint_id: str
    constraint_type: ConstraintType
    expression: str  # Human-readable expression
    smt_expression: str  # SMT-LIB format expression
    variables: List[str]  # Variable names involved
    source: ConstraintSource
    source_reference: str  # Reference to source document/rule
    priority: int = 0  # Higher priority constraints evaluated first
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def disable(self):
        """Disable this constraint."""
        self.enabled = False
        self.updated_at = datetime.now()
    
    def enable(self):
        """Enable this constraint."""
        self.enabled = True
        self.updated_at = datetime.now()
    
    def update_expression(self, new_expression: str, new_smt: str):
        """Update the constraint expression."""
        self.expression = new_expression
        self.smt_expression = new_smt
        self.updated_at = datetime.now()
    
    def get_hash(self) -> str:
        """Get hash of constraint for change detection."""
        content = f"{self.constraint_id}:{self.smt_expression}:{self.enabled}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class ConstraintGroup:
    """Groups related constraints together."""
    group_id: str
    name: str
    description: str
    constraints: List[str]  # List of constraint IDs
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class DynamicConstraintManager:
    """
    Manages dynamic constraint lifecycle for the neuro-symbolic solver.
    
    Features:
    - Add/remove/update constraints at runtime
    - Group constraints by source or category
    - Track constraint provenance and versioning
    - Export constraints in solver-ready format
    - Detect conflicts between constraints
    """
    
    def __init__(self, manager_id: str):
        self.manager_id = manager_id
        self.constraints: Dict[str, Constraint] = {}
        self.constraint_groups: Dict[str, ConstraintGroup] = {}
        self.variable_definitions: Dict[str, ConstraintVariable] = {}
        self._change_log: List[Dict[str, Any]] = []
    
    def register_variable(self, variable: ConstraintVariable):
        """Register a new variable for use in constraints."""
        self.variable_definitions[variable.name] = variable
        self._log_change("variable_registered", {"name": variable.name})
    
    def add_constraint(self, constraint: Constraint) -> bool:
        """
        Add a new constraint to the system.
        
        Returns:
            True if added successfully, False if constraint ID already exists
        """
        if constraint.constraint_id in self.constraints:
            return False
        
        # Validate variables exist
        for var_name in constraint.variables:
            if var_name not in self.variable_definitions:
                raise ValueError(f"Undefined variable: {var_name}")
        
        self.constraints[constraint.constraint_id] = constraint
        
        # Add to default group if no group specified
        if "default" not in self.constraint_groups:
            self.constraint_groups["default"] = ConstraintGroup(
                group_id="default",
                name="Default Constraints",
                description="Automatically created default constraint group",
                constraints=[]
            )
        
        self.constraint_groups["default"].constraints.append(constraint.constraint_id)
        self._log_change("constraint_added", {
            "constraint_id": constraint.constraint_id,
            "source": constraint.source.value
        })
        
        return True
    
    def remove_constraint(self, constraint_id: str) -> bool:
        """Remove a constraint from the system."""
        if constraint_id not in self.constraints:
            return False
        
        constraint = self.constraints[constraint_id]
        constraint.disable()
        
        # Remove from all groups
        for group in self.constraint_groups.values():
            if constraint_id in group.constraints:
                group.constraints.remove(constraint_id)
        
        del self.constraints[constraint_id]
        self._log_change("constraint_removed", {"constraint_id": constraint_id})
        
        return True
    
    def update_constraint(self, constraint_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing constraint."""
        if constraint_id not in self.constraints:
            return False
        
        constraint = self.constraints[constraint_id]
        
        for key, value in updates.items():
            if hasattr(constraint, key):
                setattr(constraint, key, value)
        
        constraint.updated_at = datetime.now()
        self._log_change("constraint_updated", {
            "constraint_id": constraint_id,
            "updates": list(updates.keys())
        })
        
        return True
    
    def create_constraint_group(self, group: ConstraintGroup) -> bool:
        """Create a new constraint group."""
        if group.group_id in self.constraint_groups:
            return False
        
        self.constraint_groups[group.group_id] = group
        self._log_change("group_created", {"group_id": group.group_id})
        
        return True
    
    def add_constraint_to_group(self, group_id: str, constraint_id: str) -> bool:
        """Add a constraint to a group."""
        if group_id not in self.constraint_groups:
            return False
        if constraint_id not in self.constraints:
            return False
        
        group = self.constraint_groups[group_id]
        if constraint_id not in group.constraints:
            group.constraints.append(constraint_id)
        
        self._log_change("constraint_added_to_group", {
            "group_id": group_id,
            "constraint_id": constraint_id
        })
        
        return True
    
    def enable_constraints_by_source(self, source: ConstraintSource) -> int:
        """Enable all constraints from a specific source."""
        count = 0
        for constraint in self.constraints.values():
            if constraint.source == source:
                constraint.enable()
                count += 1
        
        self._log_change("bulk_enable", {"source": source.value, "count": count})
        return count
    
    def disable_constraints_by_source(self, source: ConstraintSource) -> int:
        """Disable all constraints from a specific source."""
        count = 0
        for constraint in self.constraints.values():
            if constraint.source == source:
                constraint.disable()
                count += 1
        
        self._log_change("bulk_disable", {"source": source.value, "count": count})
        return count
    
    def get_enabled_constraints(self) -> List[Constraint]:
        """Get all currently enabled constraints."""
        return [c for c in self.constraints.values() if c.enabled]
    
    def get_constraints_by_source(self, source: ConstraintSource) -> List[Constraint]:
        """Get all constraints from a specific source."""
        return [c for c in self.constraints.values() if c.source == source]
    
    def get_constraints_for_group(self, group_id: str) -> List[Constraint]:
        """Get all constraints in a group."""
        if group_id not in self.constraint_groups:
            return []
        
        group = self.constraint_groups[group_id]
        return [
            self.constraints[cid] 
            for cid in group.constraints 
            if cid in self.constraints
        ]
    
    def detect_conflicts(self) -> List[Dict[str, Any]]:
        """
        Detect potential conflicts between constraints.
        
        This performs static analysis to identify obviously conflicting constraints
        (e.g., x > 10 and x < 5). More complex conflict detection requires
        solver invocation.
        
        Returns:
            List of detected conflicts with details
        """
        conflicts = []
        
        # Group constraints by variable for pairwise analysis
        var_constraints: Dict[str, List[Constraint]] = {}
        for constraint in self.get_enabled_constraints():
            for var_name in constraint.variables:
                if var_name not in var_constraints:
                    var_constraints[var_name] = []
                var_constraints[var_name].append(constraint)
        
        # Check for obvious bound conflicts
        for var_name, constraints in var_constraints.items():
            if var_name not in self.variable_definitions:
                continue
            
            var_def = self.variable_definitions[var_name]
            effective_lower = var_def.lower_bound
            effective_upper = var_def.upper_bound
            
            for constraint in constraints:
                # Parse simple inequality constraints
                if constraint.constraint_type == ConstraintType.LINEAR_INEQUALITY:
                    # This is simplified - real implementation would parse the expression
                    if ">=" in constraint.expression or ">" in constraint.expression:
                        # Extract lower bound if possible
                        pass
                    if "<=" in constraint.expression or "<" in constraint.expression:
                        # Extract upper bound if possible
                        pass
            
            if effective_lower is not None and effective_upper is not None:
                if effective_lower > effective_upper:
                    conflicts.append({
                        "type": "bound_conflict",
                        "variable": var_name,
                        "lower_bound": effective_lower,
                        "upper_bound": effective_upper,
                        "message": f"Variable {var_name} has impossible bounds: [{effective_lower}, {effective_upper}]"
                    })
        
        self._log_change("conflict_detection_run", {"conflicts_found": len(conflicts)})
        return conflicts
    
    def export_to_smt_lib(self, include_disabled: bool = False) -> str:
        """
        Export all constraints in SMT-LIB format.
        
        Args:
            include_disabled: Whether to include disabled constraints
            
        Returns:
            SMT-LIB formatted string ready for solver consumption
        """
        lines = ["; Auto-generated SMT-LIB constraints", "; Generated by DynamicConstraintManager"]
        lines.append(f"; Manager ID: {self.manager_id}")
        lines.append(f"; Timestamp: {datetime.now().isoformat()}")
        lines.append("")
        
        # Declare variables
        lines.append("; Variable Declarations")
        for var in self.variable_definitions.values():
            lines.append(var.to_smt_lib())
        lines.append("")
        
        # Add assertions for constraints
        lines.append("; Constraint Assertions")
        constraints_to_export = (
            self.constraints.values() 
            if include_disabled 
            else self.get_enabled_constraints()
        )
        
        for constraint in sorted(constraints_to_export, key=lambda c: c.priority, reverse=True):
            lines.append(f"; Constraint: {constraint.constraint_id}")
            lines.append(f"; Source: {constraint.source.value}")
            lines.append(f"; Expression: {constraint.expression}")
            lines.append(f"(assert {constraint.smt_expression})")
            lines.append("")
        
        lines.append("(check-sat)")
        lines.append("(get-model)")
        
        return "\n".join(lines)
    
    def export_state_dict(self) -> Dict[str, Any]:
        """Export constraint manager state as dictionary."""
        return {
            "manager_id": self.manager_id,
            "total_constraints": len(self.constraints),
            "enabled_constraints": len(self.get_enabled_constraints()),
            "constraint_groups": len(self.constraint_groups),
            "variables": len(self.variable_definitions),
            "constraints": [
                {
                    "id": c.constraint_id,
                    "type": c.constraint_type.value,
                    "expression": c.expression,
                    "source": c.source.value,
                    "enabled": c.enabled,
                    "priority": c.priority,
                    "hash": c.get_hash()
                }
                for c in self.constraints.values()
            ],
            "last_updated": max(
                (c.updated_at for c in self.constraints.values()),
                default=datetime.now()
            ).isoformat()
        }
    
    def _log_change(self, change_type: str, details: Dict[str, Any]):
        """Log a change for audit trail."""
        self._change_log.append({
            "timestamp": datetime.now().isoformat(),
            "change_type": change_type,
            "details": details
        })
    
    def get_change_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent change log entries."""
        return self._change_log[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get constraint manager statistics."""
        source_counts = {}
        for constraint in self.constraints.values():
            source = constraint.source.value
            if source not in source_counts:
                source_counts[source] = {"total": 0, "enabled": 0}
            source_counts[source]["total"] += 1
            if constraint.enabled:
                source_counts[source]["enabled"] += 1
        
        return {
            "manager_id": self.manager_id,
            "total_constraints": len(self.constraints),
            "enabled_constraints": len(self.get_enabled_constraints()),
            "disabled_constraints": len(self.constraints) - len(self.get_enabled_constraints()),
            "constraint_groups": len(self.constraint_groups),
            "variables_defined": len(self.variable_definitions),
            "by_source": source_counts,
            "recent_changes": len(self._change_log)
        }
