"""
Unsatisfiable Core Analyzer

Analyzes UNSAT cores from failed compliance checks to identify
the minimal set of conflicting constraints and enable solution synthesis.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime


@dataclass
class ConflictAnalysis:
    """Analysis result for an unsatisfiable core."""
    analysis_id: str
    unsat_core: List[str]
    timestamp: datetime
    
    # Classification of conflicts
    conflict_type: str  # "regulatory", "portfolio", "application_data", "mixed"
    
    # Minimal unsatisfiable subset
    minimal_core: List[str]
    
    # Suggested relaxations
    relaxation_suggestions: List[Dict[str, Any]]
    
    # Root cause analysis
    root_causes: List[str]
    
    # Impact assessment
    affected_constraints: List[str]
    affected_variables: List[str]


class UnsatisfiableCoreAnalyzer:
    """
    Analyzes unsatisfiable cores to enable intelligent solution synthesis.
    
    When the SMT solver returns UNSAT, this component:
    1. Identifies the minimal unsatisfiable core
    2. Classifies the type of conflict
    3. Suggests constraint relaxations
    4. Provides root cause analysis
    """
    
    def __init__(self, analyzer_id: str):
        self.analyzer_id = analyzer_id
        self.analysis_history: List[ConflictAnalysis] = []
        self._constraint_metadata: Dict[str, Dict[str, Any]] = {}
    
    def register_constraint_metadata(self, constraint_id: str, metadata: Dict[str, Any]):
        """Register metadata about a constraint for better analysis."""
        self._constraint_metadata[constraint_id] = metadata
    
    def analyze_unsat_core(
        self, 
        unsat_core: List[str],
        application_context: Dict[str, Any]
    ) -> ConflictAnalysis:
        """
        Analyze an unsatisfiable core to understand the conflict.
        
        Args:
            unsat_core: List of constraint IDs in the unsat core
            application_context: Context about the application being evaluated
            
        Returns:
            ConflictAnalysis with detailed findings
        """
        analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        # Find minimal unsatisfiable subset
        minimal_core = self._find_minimal_core(unsat_core, application_context)
        
        # Classify conflict type
        conflict_type = self._classify_conflict(minimal_core)
        
        # Generate relaxation suggestions
        relaxations = self._generate_relaxation_suggestions(minimal_core, application_context)
        
        # Perform root cause analysis
        root_causes = self._analyze_root_causes(minimal_core, application_context)
        
        # Identify affected elements
        affected_constraints = minimal_core
        affected_variables = self._extract_affected_variables(minimal_core)
        
        analysis = ConflictAnalysis(
            analysis_id=analysis_id,
            unsat_core=unsat_core,
            timestamp=datetime.now(),
            conflict_type=conflict_type,
            minimal_core=minimal_core,
            relaxation_suggestions=relaxations,
            root_causes=root_causes,
            affected_constraints=affected_constraints,
            affected_variables=affected_variables
        )
        
        self.analysis_history.append(analysis)
        return analysis
    
    def _find_minimal_core(
        self, 
        unsat_core: List[str],
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Find the minimal subset of constraints that is still unsatisfiable.
        
        Uses a simple deletion-based approach (in production, use more
        sophisticated algorithms like QuickXPlain).
        """
        if len(unsat_core) <= 1:
            return unsat_core
        
        minimal = list(unsat_core)
        
        # Try removing each constraint and check if still unsatisfiable
        # This is simplified - real implementation would re-invoke solver
        for i in range(len(minimal)):
            candidate = minimal[:i] + minimal[i+1:]
            
            # Simulate checking if subset is still unsatisfiable
            # In production, this would invoke the solver with subset
            if self._is_still_unsat(candidate, context):
                minimal = candidate
                break
        
        return minimal
    
    def _is_still_unsat(self, constraint_subset: List[str], context: Dict[str, Any]) -> bool:
        """Check if a subset of constraints is still unsatisfiable."""
        # Simplified heuristic: if subset has fewer than 2 constraints, likely satisfiable
        if len(constraint_subset) < 2:
            return False
        
        # In production, would invoke solver with subset
        # For now, assume removing one constraint resolves the conflict
        return True
    
    def _classify_conflict(self, minimal_core: List[str]) -> str:
        """Classify the type of conflict based on constraint sources."""
        regulatory_count = 0
        portfolio_count = 0
        application_count = 0
        
        for constraint_id in minimal_core:
            metadata = self._constraint_metadata.get(constraint_id, {})
            source = metadata.get("source", "unknown")
            
            if "regulatory" in source.lower():
                regulatory_count += 1
            elif "portfolio" in source.lower():
                portfolio_count += 1
            elif "application" in source.lower():
                application_count += 1
        
        if regulatory_count > 0 and portfolio_count > 0:
            return "mixed_regulatory_portfolio"
        elif regulatory_count > portfolio_count:
            return "regulatory"
        elif portfolio_count > application_count:
            return "portfolio"
        else:
            return "application_data"
    
    def _generate_relaxation_suggestions(
        self,
        minimal_core: List[str],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate suggestions for relaxing constraints to achieve SAT."""
        suggestions = []
        
        for constraint_id in minimal_core:
            metadata = self._constraint_metadata.get(constraint_id, {})
            
            suggestion = {
                "constraint_id": constraint_id,
                "relaxation_type": "none",
                "suggested_change": None,
                "impact": "unknown",
                "feasibility": "requires_review"
            }
            
            # Analyze constraint type for relaxation options
            expression = metadata.get("expression", "")
            
            if ">=" in expression:
                # Lower bound constraint - suggest lowering threshold
                suggestion["relaxation_type"] = "lower_threshold"
                suggestion["suggested_change"] = "Reduce minimum requirement by 5-10%"
                suggestion["impact"] = "May increase risk exposure"
            elif "<=" in expression:
                # Upper bound constraint - suggest raising threshold
                suggestion["relaxation_type"] = "raise_threshold"
                suggestion["suggested_change"] = "Increase maximum limit by 5-10%"
                suggestion["impact"] = "May increase concentration risk"
            elif "=" in expression:
                # Equality constraint - suggest allowing range
                suggestion["relaxation_type"] = "allow_range"
                suggestion["suggested_change"] = "Convert to inequality with tolerance band"
                suggestion["impact"] = "Adds flexibility but reduces precision"
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _analyze_root_causes(
        self,
        minimal_core: List[str],
        context: Dict[str, Any]
    ) -> List[str]:
        """Perform root cause analysis of the conflict."""
        causes = []
        
        # Check for common patterns
        if len(minimal_core) == 2:
            causes.append(f"Direct conflict between two constraints: {minimal_core[0]} and {minimal_core[1]}")
        
        # Check for threshold violations
        app_data = context.get("application_data", {})
        for constraint_id in minimal_core:
            metadata = self._constraint_metadata.get(constraint_id, {})
            expression = metadata.get("expression", "")
            
            if ">=" in expression:
                causes.append(f"Value below minimum threshold in constraint {constraint_id}")
            elif "<=" in expression:
                causes.append(f"Value exceeds maximum threshold in constraint {constraint_id}")
        
        # Check for portfolio-level issues
        if context.get("ledger_state"):
            causes.append("Portfolio state contributing to constraint violation")
        
        if not causes:
            causes.append("Complex multi-constraint interaction causing infeasibility")
        
        return causes
    
    def _extract_affected_variables(self, minimal_core: List[str]) -> List[str]:
        """Extract variables involved in the unsatisfiable core."""
        variables = set()
        
        for constraint_id in minimal_core:
            metadata = self._constraint_metadata.get(constraint_id, {})
            vars_in_constraint = metadata.get("variables", [])
            variables.update(vars_in_constraint)
        
        return list(variables)
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get statistics on conflict analyses performed."""
        if not self.analysis_history:
            return {"total_analyses": 0}
        
        conflict_types = {}
        for analysis in self.analysis_history:
            ct = analysis.conflict_type
            conflict_types[ct] = conflict_types.get(ct, 0) + 1
        
        avg_core_size = sum(len(a.minimal_core) for a in self.analysis_history) / len(self.analysis_history)
        
        return {
            "analyzer_id": self.analyzer_id,
            "total_analyses": len(self.analysis_history),
            "by_conflict_type": conflict_types,
            "average_core_size": avg_core_size,
            "average_suggestions_per_analysis": sum(len(a.relaxation_suggestions) for a in self.analysis_history) / len(self.analysis_history)
        }
