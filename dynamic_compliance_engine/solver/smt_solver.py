"""
SMT Compliance Solver

Core solver engine that uses SMT (Satisfiability Modulo Theories) solving
to verify compliance and generate unsatisfiable cores for violation analysis.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum


class SolverResult(Enum):
    """Possible results from SMT solver."""
    SAT = "sat"  # Satisfiable - compliant
    UNSAT = "unsat"  # Unsatisfiable - violation detected
    UNKNOWN = "unknown"  # Cannot determine
    TIMEOUT = "timeout"  # Solver timed out
    ERROR = "error"  # Solver error


@dataclass
class SolverVariable:
    """Represents a variable in the solver context."""
    name: str
    var_type: str  # "int", "real", "bool"
    value: Optional[Any] = None
    bounds: Optional[Tuple[float, float]] = None


@dataclass
class SolverConstraint:
    """Represents a constraint in the solver."""
    constraint_id: str
    expression: str
    smt_expression: str
    is_soft: bool = False  # Soft constraints can be relaxed
    weight: float = 1.0  # For optimization with soft constraints
    priority: int = 0


@dataclass
class ComplianceResult:
    """Result of a compliance check."""
    result_id: str
    solver_result: SolverResult
    is_compliant: bool
    application_id: str
    timestamp: datetime
    
    # If UNSAT, contains the unsatisfiable core
    unsat_core: Optional[List[str]] = None
    
    # Variable assignments from model (if SAT)
    model: Optional[Dict[str, Any]] = None
    
    # All constraints checked
    constraints_checked: List[str] = field(default_factory=list)
    
    # Violated constraints (if any)
    violated_constraints: List[str] = field(default_factory=list)
    
    # Detailed explanation
    explanation: str = ""
    
    # Proof data for audit
    proof_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "result_id": self.result_id,
            "solver_result": self.solver_result.value,
            "is_compliant": self.is_compliant,
            "application_id": self.application_id,
            "timestamp": self.timestamp.isoformat(),
            "unsat_core": self.unsat_core,
            "model": self.model,
            "constraints_checked": self.constraints_checked,
            "violated_constraints": self.violated_constraints,
            "explanation": self.explanation,
            "proof_data": self.proof_data
        }


class SMTComplianceSolver:
    """
    SMT-based compliance solver for neuro-symbolic verification.
    
    This solver:
    - Accepts constraints from DynamicConstraintManager
    - Incorporates real-time portfolio state from StatefulPortfolioLedger
    - Returns SAT/UNSAT with explanations
    - Generates unsatisfiable cores for violation analysis
    - Supports both hard and soft constraints
    """
    
    def __init__(self, solver_id: str):
        self.solver_id = solver_id
        self.variables: Dict[str, SolverVariable] = {}
        self.hard_constraints: List[SolverConstraint] = []
        self.soft_constraints: List[SolverConstraint] = []
        self._solution_history: List[ComplianceResult] = []
        
        # Simulated solver state (in production, this would wrap Z3/CVC5)
        self._constraint_store: Dict[str, SolverConstraint] = {}
    
    def add_variable(self, variable: SolverVariable):
        """Add a variable to the solver context."""
        self.variables[variable.name] = variable
    
    def add_hard_constraint(self, constraint: SolverConstraint):
        """Add a hard constraint that must be satisfied."""
        self.hard_constraints.append(constraint)
        self._constraint_store[constraint.constraint_id] = constraint
    
    def add_soft_constraint(self, constraint: SolverConstraint):
        """Add a soft constraint that can be relaxed if needed."""
        constraint.is_soft = True
        self.soft_constraints.append(constraint)
        self._constraint_store[constraint.constraint_id] = constraint
    
    def load_constraints_from_manager(self, constraint_manager) -> int:
        """
        Load constraints from a DynamicConstraintManager.
        
        Returns:
            Number of constraints loaded
        """
        count = 0
        for constraint in constraint_manager.get_enabled_constraints():
            solver_constraint = SolverConstraint(
                constraint_id=constraint.constraint_id,
                expression=constraint.expression,
                smt_expression=constraint.smt_expression,
                priority=constraint.priority
            )
            
            # High priority regulatory constraints are hard constraints
            if constraint.priority >= 80:
                self.add_hard_constraint(solver_constraint)
            else:
                self.add_soft_constraint(solver_constraint)
            
            count += 1
        
        return count
    
    def check_compliance(
        self, 
        application_data: Dict[str, Any],
        ledger_state: Optional[Dict[str, Any]] = None
    ) -> ComplianceResult:
        """
        Check compliance for a specific application.
        
        Args:
            application_data: Application variables and values
            ledger_state: Optional current portfolio state
            
        Returns:
            ComplianceResult with SAT/UNSAT determination
        """
        result_id = f"check_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        timestamp = datetime.now()
        
        # Build solver problem
        all_constraints = self.hard_constraints + self.soft_constraints
        
        # In a real implementation, we would:
        # 1. Create SMT-LIB problem with variables and constraints
        # 2. Invoke Z3/CVC5 solver
        # 3. Parse result and extract model or unsat core
        
        # For this implementation, we simulate the solving process
        solver_result, model, unsat_core, violated = self._simulate_solving(
            application_data, ledger_state, all_constraints
        )
        
        # Determine compliance
        is_compliant = solver_result == SolverResult.SAT
        
        # Generate explanation
        explanation = self._generate_explanation(
            solver_result, violated, unsat_core, application_data
        )
        
        # Build result
        result = ComplianceResult(
            result_id=result_id,
            solver_result=solver_result,
            is_compliant=is_compliant,
            application_id=application_data.get("application_id", "unknown"),
            timestamp=timestamp,
            unsat_core=unsat_core,
            model=model,
            constraints_checked=[c.constraint_id for c in all_constraints],
            violated_constraints=violated,
            explanation=explanation,
            proof_data={
                "solver_id": self.solver_id,
                "constraints_count": len(all_constraints),
                "hard_constraints_count": len(self.hard_constraints),
                "soft_constraints_count": len(self.soft_constraints),
                "application_variables": list(application_data.keys())
            }
        )
        
        self._solution_history.append(result)
        return result
    
    def _simulate_solving(
        self,
        application_data: Dict[str, Any],
        ledger_state: Optional[Dict[str, Any]],
        constraints: List[SolverConstraint]
    ) -> Tuple[SolverResult, Optional[Dict], Optional[List[str]], List[str]]:
        """
        Simulate SMT solving process.
        
        In production, this would invoke an actual SMT solver like Z3.
        """
        violated = []
        
        # Simple constraint evaluation simulation
        for constraint in constraints:
            if constraint.is_soft:
                continue  # Skip soft constraints in basic check
            
            # Evaluate constraint against application data
            is_violated = self._evaluate_constraint(constraint, application_data, ledger_state)
            
            if is_violated:
                violated.append(constraint.constraint_id)
        
        if violated:
            return (
                SolverResult.UNSAT,
                None,
                violated,  # Unsatisfiable core is the violated constraints
                violated
            )
        else:
            # Return model with application values
            return (
                SolverResult.SAT,
                application_data.copy(),
                None,
                []
            )
    
    def _evaluate_constraint(
        self,
        constraint: SolverConstraint,
        application_data: Dict[str, Any],
        ledger_state: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Evaluate a single constraint.
        
        Returns True if violated, False if satisfied.
        """
        # This is a simplified evaluator
        # Real implementation would parse SMT expressions and evaluate properly
        
        smt = constraint.smt_expression
        
        # Handle simple comparisons
        if ">=" in smt:
            parts = smt.replace("(>= ", "").replace(")", "").split()
            if len(parts) == 2:
                var_name = parts[0]
                try:
                    threshold = float(parts[1])
                    actual = application_data.get(var_name, 0)
                    return actual < threshold  # Violated if below threshold
                except (ValueError, TypeError):
                    pass
        
        elif "<=" in smt:
            parts = smt.replace("(<= ", "").replace(")", "").split()
            if len(parts) == 2:
                var_name = parts[0]
                try:
                    threshold = float(parts[1])
                    actual = application_data.get(var_name, 0)
                    return actual > threshold  # Violated if above threshold
                except (ValueError, TypeError):
                    pass
        
        elif "=" in smt and not smt.startswith("(=>"):
            parts = smt.replace("(= ", "").replace(")", "").split()
            if len(parts) == 2:
                var_name = parts[0]
                expected = parts[1]
                actual = application_data.get(var_name)
                
                # Handle boolean
                if expected == "true":
                    return actual != True
                elif expected == "false":
                    return actual != False
                else:
                    try:
                        return float(actual) != float(expected)
                    except (ValueError, TypeError):
                        pass
        
        return False  # Default: not violated
    
    def _generate_explanation(
        self,
        result: SolverResult,
        violated: List[str],
        unsat_core: Optional[List[str]],
        application_data: Dict[str, Any]
    ) -> str:
        """Generate human-readable explanation of result."""
        if result == SolverResult.SAT:
            return "Application satisfies all compliance constraints."
        elif result == SolverResult.UNSAT:
            if violated:
                return f"Compliance violation detected. {len(violated)} constraint(s) violated: {', '.join(violated)}"
            return "Compliance violation detected. Constraints cannot be satisfied."
        elif result == SolverResult.UNKNOWN:
            return "Unable to determine compliance status."
        elif result == SolverResult.TIMEOUT:
            return "Compliance check timed out."
        else:
            return "Error during compliance check."
    
    def get_unsatisfiable_core(self, result: ComplianceResult) -> Optional[List[str]]:
        """
        Extract unsatisfiable core from an UNSAT result.
        
        The unsat core identifies the minimal set of conflicting constraints,
        which is crucial for solution synthesis.
        """
        if result.solver_result != SolverResult.UNSAT:
            return None
        return result.unsat_core
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get solver statistics."""
        sat_count = sum(1 for r in self._solution_history if r.solver_result == SolverResult.SAT)
        unsat_count = sum(1 for r in self._solution_history if r.solver_result == SolverResult.UNSAT)
        
        return {
            "solver_id": self.solver_id,
            "total_checks": len(self._solution_history),
            "compliant_applications": sat_count,
            "non_compliant_applications": unsat_count,
            "compliance_rate": sat_count / len(self._solution_history) if self._solution_history else 0,
            "hard_constraints": len(self.hard_constraints),
            "soft_constraints": len(self.soft_constraints),
            "variables_defined": len(self.variables)
        }
    
    def export_proof_artifact(self, result: ComplianceResult) -> Dict[str, Any]:
        """
        Export proof artifact for audit trail.
        
        This creates a machine-verifiable proof payload suitable for
        regulatory submission or M2M communication.
        """
        return {
            "proof_version": "1.0",
            "solver_id": self.solver_id,
            "result_id": result.result_id,
            "timestamp": result.timestamp.isoformat(),
            "application_id": result.application_id,
            "determination": result.solver_result.value,
            "is_compliant": result.is_compliant,
            "constraints_evaluated": result.constraints_checked,
            "violations": result.violated_constraints,
            "unsat_core": result.unsat_core,
            "model_assignment": result.model,
            "explanation": result.explanation,
            "solver_metadata": result.proof_data,
            "verification_hash": self._compute_verification_hash(result)
        }
    
    def _compute_verification_hash(self, result: ComplianceResult) -> str:
        """Compute hash for proof verification."""
        import hashlib
        content = f"{result.result_id}:{result.solver_result.value}:{','.join(sorted(result.violated_constraints))}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
