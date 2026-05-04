"""
Compliant Solution Synthesizer

Transforms violation detection into constraint relaxation and solution synthesis.
When compliance fails, this component generates alternative structures that achieve
a "Pass" state through adjusted parameters (pricing, limits, terms).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum


class SynthesisStrategy(Enum):
    """Strategies for synthesizing compliant solutions."""
    PARAMETER_ADJUSTMENT = "parameter_adjustment"  # Adjust numerical values
    CONSTRAINT_RELAXATION = "constraint_relaxation"  # Relax soft constraints
    STRUCTURAL_CHANGE = "structural_change"  # Change deal structure
    HYBRID = "hybrid"  # Combine multiple strategies


@dataclass
class SynthesizedSolution:
    """A synthesized compliant solution alternative."""
    solution_id: str
    original_application: Dict[str, Any]
    modified_application: Dict[str, Any]
    
    # Changes made to achieve compliance
    changes: List[Dict[str, Any]]
    
    # Strategy used
    strategy: SynthesisStrategy
    
    # Compliance status after modification
    is_compliant: bool
    
    # Quality metrics
    similarity_score: float  # How similar to original (0-1)
    feasibility_score: float  # Business feasibility (0-1)
    customer_impact: str  # "low", "medium", "high"
    
    # Explanation
    explanation: str
    
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "solution_id": self.solution_id,
            "changes": self.changes,
            "strategy": self.strategy.value,
            "is_compliant": self.is_compliant,
            "similarity_score": self.similarity_score,
            "feasibility_score": self.feasibility_score,
            "customer_impact": self.customer_impact,
            "explanation": self.explanation,
            "modified_values": self.modified_application
        }


class CompliantSolutionSynthesizer:
    """
    Synthesizes compliant alternatives from failed compliance checks.
    
    Instead of binary Fail/Decline, this component:
    1. Analyzes the unsatisfiable core
    2. Identifies adjustable parameters
    3. Generates alternative solutions that satisfy constraints
    4. Ranks solutions by business criteria
    """
    
    def __init__(self, synthesizer_id: str):
        self.synthesizer_id = synthesizer_id
        self.synthesis_history: List[SynthesizedSolution] = []
        self._adjustable_parameters: Dict[str, Dict[str, Any]] = {}
        self._relaxation_rules: List[Dict[str, Any]] = []
    
    def register_adjustable_parameter(
        self, 
        param_name: str, 
        adjustment_rules: Dict[str, Any]
    ):
        """
        Register a parameter that can be adjusted during synthesis.
        
        Args:
            param_name: Name of the adjustable parameter
            adjustment_rules: Rules for how parameter can be adjusted
                - min_value: Minimum allowed value
                - max_value: Maximum allowed value
                - step_size: Increment/decrement step
                - adjustment_type: "increase", "decrease", "both"
                - business_impact: Impact on business metrics
        """
        self._adjustable_parameters[param_name] = adjustment_rules
    
    def add_relaxation_rule(self, rule: Dict[str, Any]):
        """Add a rule for constraint relaxation."""
        self._relaxation_rules.append(rule)
    
    def synthesize_solutions(
        self,
        original_application: Dict[str, Any],
        violated_constraints: List[str],
        constraint_metadata: Dict[str, Dict[str, Any]],
        max_solutions: int = 5
    ) -> List[SynthesizedSolution]:
        """
        Synthesize compliant alternative solutions.
        
        Args:
            original_application: Original application that failed compliance
            violated_constraints: List of violated constraint IDs
            constraint_metadata: Metadata about each constraint
            max_solutions: Maximum number of solutions to generate
            
        Returns:
            List of synthesized solutions ranked by quality
        """
        solutions = []
        
        # Strategy 1: Parameter Adjustment
        param_solutions = self._synthesize_parameter_adjustments(
            original_application, violated_constraints, constraint_metadata
        )
        solutions.extend(param_solutions)
        
        # Strategy 2: Constraint Relaxation (for soft constraints)
        relaxation_solutions = self._synthesize_constraint_relaxations(
            original_application, violated_constraints, constraint_metadata
        )
        solutions.extend(relaxation_solutions)
        
        # Strategy 3: Structural Changes
        structural_solutions = self._synthesize_structural_changes(
            original_application, violated_constraints, constraint_metadata
        )
        solutions.extend(structural_solutions)
        
        # Rank and filter solutions
        ranked_solutions = self._rank_solutions(solutions, original_application)
        
        # Return top N solutions
        return ranked_solutions[:max_solutions]
    
    def _synthesize_parameter_adjustments(
        self,
        original: Dict[str, Any],
        violations: List[str],
        metadata: Dict[str, Dict[str, Any]]
    ) -> List[SynthesizedSolution]:
        """Generate solutions by adjusting numerical parameters."""
        solutions = []
        
        for constraint_id in violations:
            constraint_meta = metadata.get(constraint_id, {})
            expression = constraint_meta.get("expression", "")
            
            # Identify which parameter to adjust
            adjustable_params = self._find_adjustable_params(expression, original)
            
            for param_name, current_value in adjustable_params.items():
                if param_name not in self._adjustable_parameters:
                    continue
                
                rules = self._adjustable_parameters[param_name]
                
                # Calculate adjustment needed
                adjustments = self._calculate_adjustments(
                    param_name, current_value, expression, rules
                )
                
                for adjustment in adjustments:
                    modified = original.copy()
                    modified[param_name] = adjustment["new_value"]
                    
                    solution = SynthesizedSolution(
                        solution_id=f"solution_param_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                        original_application=original,
                        modified_application=modified,
                        changes=[{
                            "parameter": param_name,
                            "original_value": current_value,
                            "new_value": adjustment["new_value"],
                            "change_type": "parameter_adjustment",
                            "reason": f"To satisfy constraint {constraint_id}"
                        }],
                        strategy=SynthesisStrategy.PARAMETER_ADJUSTMENT,
                        is_compliant=True,  # Would verify with solver
                        similarity_score=self._calculate_similarity(original, modified),
                        feasibility_score=adjustment.get("feasibility", 0.8),
                        customer_impact=adjustment.get("impact", "medium"),
                        explanation=f"Adjusted {param_name} from {current_value} to {adjustment['new_value']} to meet requirement"
                    )
                    
                    solutions.append(solution)
        
        return solutions
    
    def _synthesize_constraint_relaxations(
        self,
        original: Dict[str, Any],
        violations: List[str],
        metadata: Dict[str, Dict[str, Any]]
    ) -> List[SynthesizedSolution]:
        """Generate solutions by relaxing soft constraints."""
        solutions = []
        
        for constraint_id in violations:
            constraint_meta = metadata.get(constraint_id, {})
            
            # Check if constraint can be relaxed
            if constraint_meta.get("is_soft", False):
                # Generate solution with relaxed constraint
                solution = SynthesizedSolution(
                    solution_id=f"solution_relax_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                    original_application=original,
                    modified_application=original.copy(),
                    changes=[{
                        "constraint_id": constraint_id,
                        "change_type": "constraint_relaxation",
                        "reason": "Soft constraint relaxed based on business rules"
                    }],
                    strategy=SynthesisStrategy.CONSTRAINT_RELAXATION,
                    is_compliant=True,
                    similarity_score=1.0,  # No change to application
                    feasibility_score=0.7,  # Requires approval
                    customer_impact="low",
                    explanation=f"Relaxed soft constraint {constraint_id} per policy guidelines"
                )
                
                solutions.append(solution)
        
        return solutions
    
    def _synthesize_structural_changes(
        self,
        original: Dict[str, Any],
        violations: List[str],
        metadata: Dict[str, Dict[str, Any]]
    ) -> List[SynthesizedSolution]:
        """Generate solutions through structural deal changes."""
        solutions = []
        
        # Example: Suggest collateral addition to reduce exposure
        if "loan_amount" in original:
            loan_amount = original.get("loan_amount", 0)
            current_collateral = original.get("collateral_value", 0)
            
            # Suggest increased collateral
            suggested_collateral = loan_amount * 0.8  # 80% LTV
            
            if suggested_collateral > current_collateral:
                modified = original.copy()
                modified["collateral_value"] = suggested_collateral
                
                solution = SynthesizedSolution(
                    solution_id=f"solution_struct_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                    original_application=original,
                    modified_application=modified,
                    changes=[{
                        "parameter": "collateral_value",
                        "original_value": current_collateral,
                        "new_value": suggested_collateral,
                        "change_type": "structural_change",
                        "reason": "Increase collateral to improve LTV ratio"
                    }],
                    strategy=SynthesisStrategy.STRUCTURAL_CHANGE,
                    is_compliant=True,
                    similarity_score=self._calculate_similarity(original, modified),
                    feasibility_score=0.6,  # Requires customer action
                    customer_impact="medium",
                    explanation=f"Adding ${suggested_collateral - current_collateral:,.2f} in collateral would achieve compliance"
                )
                
                solutions.append(solution)
        
        return solutions
    
    def _find_adjustable_params(
        self, 
        expression: str, 
        application: Dict[str, Any]
    ) -> Dict[str, float]:
        """Find parameters in expression that can be adjusted."""
        adjustable = {}
        
        # Simple extraction - look for variable names in expression
        import re
        var_pattern = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*')
        variables = var_pattern.findall(expression)
        
        for var in variables:
            if var in application:
                value = application[var]
                if isinstance(value, (int, float)):
                    adjustable[var] = value
        
        return adjustable
    
    def _calculate_adjustments(
        self,
        param_name: str,
        current_value: float,
        expression: str,
        rules: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Calculate possible adjustments for a parameter."""
        adjustments = []
        
        min_val = rules.get("min_value", 0)
        max_val = rules.get("max_value", float('inf'))
        step = rules.get("step_size", current_value * 0.05)  # Default 5% steps
        adj_type = rules.get("adjustment_type", "both")
        
        # Determine direction based on constraint
        if ">=" in expression:
            # Need to increase value
            if adj_type in ["increase", "both"]:
                new_val = min(current_value + step, max_val)
                if new_val != current_value:
                    adjustments.append({
                        "new_value": new_val,
                        "direction": "increase",
                        "feasibility": 0.8,
                        "impact": "low"
                    })
        elif "<=" in expression:
            # Need to decrease value
            if adj_type in ["decrease", "both"]:
                new_val = max(current_value - step, min_val)
                if new_val != current_value:
                    adjustments.append({
                        "new_value": new_val,
                        "direction": "decrease",
                        "feasibility": 0.8,
                        "impact": "medium"
                    })
        
        return adjustments
    
    def _calculate_similarity(self, original: Dict, modified: Dict) -> float:
        """Calculate similarity score between original and modified applications."""
        if not original:
            return 0.0
        
        changed_count = 0
        total_count = len(original)
        
        for key in original:
            if key in modified and original[key] != modified[key]:
                changed_count += 1
        
        return 1.0 - (changed_count / total_count) if total_count > 0 else 1.0
    
    def _rank_solutions(
        self,
        solutions: List[SynthesizedSolution],
        original: Dict[str, Any]
    ) -> List[SynthesizedSolution]:
        """Rank solutions by quality metrics."""
        # Score based on similarity and feasibility
        for solution in solutions:
            solution._quality_score = (
                solution.similarity_score * 0.5 +
                solution.feasibility_score * 0.5
            )
        
        # Sort by quality score descending
        solutions.sort(key=lambda s: getattr(s, '_quality_score', 0), reverse=True)
        
        return solutions
    
    def get_synthesis_statistics(self) -> Dict[str, Any]:
        """Get statistics on solution synthesis."""
        if not self.synthesis_history:
            return {"total_syntheses": 0}
        
        strategy_counts = {}
        for sol in self.synthesis_history:
            strat = sol.strategy.value
            strategy_counts[strat] = strategy_counts.get(strat, 0) + 1
        
        avg_similarity = sum(s.similarity_score for s in self.synthesis_history) / len(self.synthesis_history)
        avg_feasibility = sum(s.feasibility_score for s in self.synthesis_history) / len(self.synthesis_history)
        
        return {
            "synthesizer_id": self.synthesizer_id,
            "total_solutions_generated": len(self.synthesis_history),
            "by_strategy": strategy_counts,
            "average_similarity_score": avg_similarity,
            "average_feasibility_score": avg_feasibility,
            "compliance_rate": sum(1 for s in self.synthesis_history if s.is_compliant) / len(self.synthesis_history)
        }
