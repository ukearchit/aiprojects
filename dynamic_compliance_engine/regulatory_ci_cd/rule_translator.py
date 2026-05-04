"""
Rule Translator

Translates extracted regulatory rules into executable SMT solver constraints.
This is the core of the Automated Regulatory CI/CD pipeline.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import re

from ..core.constraint_manager import (
    Constraint, ConstraintType, ConstraintSource, ConstraintVariable,
    DynamicConstraintManager
)
from .regulatory_parser import ExtractedRule, RegulationType


@dataclass
class TranslationResult:
    """Result of translating a regulatory rule to constraints."""
    rule_id: str
    success: bool
    constraints_generated: List[Constraint]
    warnings: List[str]
    errors: List[str]
    translation_confidence: float
    source_rule: ExtractedRule
    
    @property
    def is_usable(self) -> bool:
        """Check if translation is usable (success with no critical errors)."""
        return self.success and len(self.errors) == 0


class RuleTranslator:
    """
    Translates parsed regulatory rules into executable solver constraints.
    
    This component implements the "Translate" phase of the Translate-Verify-Narrate
    pipeline for regulatory CI/CD, converting natural language regulations into
    mathematically precise SMT constraints.
    """
    
    def __init__(self, translator_id: str):
        self.translator_id = translator_id
        self.translation_history: List[TranslationResult] = []
        self._translation_templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[RegulationType, callable]:
        """Initialize translation templates for each regulation type."""
        return {
            RegulationType.CAPITAL_REQUIREMENT: self._translate_capital_requirement,
            RegulationType.CONCENTRATION_LIMIT: self._translate_concentration_limit,
            RegulationType.LIQUIDITY_RULE: self._translate_liquidity_rule,
            RegulationType.LENDING_LIMIT: self._translate_lending_limit,
            RegulationType.RISK_WEIGHT_RULE: self._translate_risk_weight_rule,
            RegulationType.REPORTING_REQUIREMENT: self._translate_reporting_requirement,
            RegulationType.DISCLOSURE_RULE: self._translate_disclosure_rule,
        }
    
    def translate_rule(
        self, 
        rule: ExtractedRule, 
        constraint_manager: DynamicConstraintManager
    ) -> TranslationResult:
        """
        Translate a single extracted rule into solver constraints.
        
        Args:
            rule: The extracted regulatory rule
            constraint_manager: Manager to register constraints with
            
        Returns:
            TranslationResult with generated constraints and status
        """
        warnings = []
        errors = []
        constraints = []
        
        # Check if we have a translation template for this rule type
        if rule.regulation_type not in self._translation_templates:
            warnings.append(f"No translation template for regulation type: {rule.regulation_type.value}")
            # Try generic translation
            constraints, errors = self._generic_translation(rule)
        else:
            # Use specific translation template
            translator_func = self._translation_templates[rule.regulation_type]
            try:
                constraints, errors = translator_func(rule)
            except Exception as e:
                errors.append(f"Translation error: {str(e)}")
        
        # Register variables and constraints
        successfully_added = []
        for constraint in constraints:
            # Ensure all variables are registered
            for var_name in constraint.variables:
                if var_name not in constraint_manager.variable_definitions:
                    # Auto-register variable with default type
                    var_type = self._infer_variable_type(var_name, constraint)
                    constraint_manager.register_variable(
                        ConstraintVariable(name=var_name, var_type=var_type)
                    )
            
            # Add constraint
            if constraint_manager.add_constraint(constraint):
                successfully_added.append(constraint.constraint_id)
            else:
                warnings.append(f"Constraint {constraint.constraint_id} already exists")
        
        # Calculate translation confidence
        confidence = self._calculate_translation_confidence(
            rule, constraints, errors, warnings
        )
        
        result = TranslationResult(
            rule_id=rule.rule_id,
            success=len(successfully_added) > 0 and len(errors) == 0,
            constraints_generated=constraints,
            warnings=warnings,
            errors=errors,
            translation_confidence=confidence,
            source_rule=rule
        )
        
        self.translation_history.append(result)
        return result
    
    def translate_batch(
        self, 
        rules: List[ExtractedRule],
        constraint_manager: DynamicConstraintManager
    ) -> List[TranslationResult]:
        """Translate multiple rules in batch."""
        results = []
        for rule in rules:
            result = self.translate_rule(rule, constraint_manager)
            results.append(result)
        return results
    
    def _translate_capital_requirement(self, rule: ExtractedRule) -> Tuple[List[Constraint], List[str]]:
        """Translate capital requirement rules."""
        constraints = []
        errors = []
        
        params = rule.parameters
        percentages = params.get('percentages', [])
        
        if not percentages:
            errors.append("No percentage threshold found in capital requirement rule")
            return constraints, errors
        
        # Standard capital ratio constraint: capital_ratio >= minimum_percentage
        min_ratio = min(percentages)  # Use most conservative
        
        constraint = Constraint(
            constraint_id=f"cap_req_{rule.rule_id}",
            constraint_type=ConstraintType.LINEAR_INEQUALITY,
            expression=f"capital_ratio >= {min_ratio}",
            smt_expression=f"(>= capital_ratio {min_ratio})",
            variables=["capital_ratio"],
            source=ConstraintSource.REGULATORY_RULE,
            source_reference=rule.source_document,
            priority=100,  # High priority for regulatory requirements
            metadata={
                "rule_type": "capital_requirement",
                "minimum_ratio": min_ratio,
                "original_rule_id": rule.rule_id
            }
        )
        
        constraints.append(constraint)
        return constraints, errors
    
    def _translate_concentration_limit(self, rule: ExtractedRule) -> Tuple[List[Constraint], List[str]]:
        """Translate concentration limit rules."""
        constraints = []
        errors = []
        
        params = rule.parameters
        percentages = params.get('percentages', [])
        
        if not percentages:
            errors.append("No percentage threshold found in concentration limit rule")
            return constraints, errors
        
        max_concentration = min(percentages)  # Most restrictive
        
        # Constraint: sector_exposure / total_exposure <= max_concentration / 100
        # Rewritten as: sector_exposure * 100 <= max_concentration * total_exposure
        constraint = Constraint(
            constraint_id=f"conc_lim_{rule.rule_id}",
            constraint_type=ConstraintType.LINEAR_INEQUALITY,
            expression=f"concentration_percentage <= {max_concentration}",
            smt_expression=f"(<= concentration_percentage {max_concentration})",
            variables=["concentration_percentage"],
            source=ConstraintSource.REGULATORY_RULE,
            source_reference=rule.source_document,
            priority=100,
            metadata={
                "rule_type": "concentration_limit",
                "max_percentage": max_concentration,
                "original_rule_id": rule.rule_id
            }
        )
        
        constraints.append(constraint)
        return constraints, errors
    
    def _translate_liquidity_rule(self, rule: ExtractedRule) -> Tuple[List[Constraint], List[str]]:
        """Translate liquidity requirement rules."""
        constraints = []
        errors = []
        
        params = rule.parameters
        percentages = params.get('percentages', [])
        
        if not percentages:
            errors.append("No percentage threshold found in liquidity rule")
            return constraints, errors
        
        min_lcr = min(percentages)
        
        constraint = Constraint(
            constraint_id=f"liq_req_{rule.rule_id}",
            constraint_type=ConstraintType.LINEAR_INEQUALITY,
            expression=f"liquidity_coverage_ratio >= {min_lcr}",
            smt_expression=f"(>= liquidity_coverage_ratio {min_lcr})",
            variables=["liquidity_coverage_ratio"],
            source=ConstraintSource.REGULATORY_RULE,
            source_reference=rule.source_document,
            priority=100,
            metadata={
                "rule_type": "liquidity_requirement",
                "min_lcr": min_lcr,
                "original_rule_id": rule.rule_id
            }
        )
        
        constraints.append(constraint)
        return constraints, errors
    
    def _translate_lending_limit(self, rule: ExtractedRule) -> Tuple[List[Constraint], List[str]]:
        """Translate lending limit rules."""
        constraints = []
        errors = []
        
        params = rule.parameters
        monetary_values = params.get('monetary_values', [])
        
        if not monetary_values:
            errors.append("No monetary threshold found in lending limit rule")
            return constraints, errors
        
        max_loan = min(monetary_values)  # Most restrictive
        
        constraint = Constraint(
            constraint_id=f"lend_lim_{rule.rule_id}",
            constraint_type=ConstraintType.LINEAR_INEQUALITY,
            expression=f"loan_amount <= {max_loan}",
            smt_expression=f"(<= loan_amount {max_loan})",
            variables=["loan_amount"],
            source=ConstraintSource.REGULATORY_RULE,
            source_reference=rule.source_document,
            priority=100,
            metadata={
                "rule_type": "lending_limit",
                "max_amount": max_loan,
                "original_rule_id": rule.rule_id
            }
        )
        
        constraints.append(constraint)
        return constraints, errors
    
    def _translate_risk_weight_rule(self, rule: ExtractedRule) -> Tuple[List[Constraint], List[str]]:
        """Translate risk weight rules."""
        constraints = []
        errors = []
        
        # Risk weight rules typically define weights for asset classes
        # This is a simplified translation
        params = rule.parameters
        percentages = params.get('percentages', [100])  # Default 100% risk weight
        
        constraint = Constraint(
            constraint_id=f"risk_wt_{rule.rule_id}",
            constraint_type=ConstraintType.LINEAR_EQUALITY,
            expression=f"risk_weight = {percentages[0]}",
            smt_expression=f"(= risk_weight {percentages[0]})",
            variables=["risk_weight"],
            source=ConstraintSource.REGULATORY_RULE,
            source_reference=rule.source_document,
            priority=50,
            metadata={
                "rule_type": "risk_weight",
                "risk_weight_pct": percentages[0],
                "original_rule_id": rule.rule_id
            }
        )
        
        constraints.append(constraint)
        return constraints, errors
    
    def _translate_reporting_requirement(self, rule: ExtractedRule) -> Tuple[List[Constraint], List[str]]:
        """Translate reporting requirements (typically boolean constraints)."""
        constraints = []
        errors = []
        
        # Reporting requirements are often procedural rather than mathematical
        # We create a boolean flag that must be true
        constraint = Constraint(
            constraint_id=f"report_req_{rule.rule_id}",
            constraint_type=ConstraintType.BOOLEAN,
            expression="reporting_compliance = true",
            smt_expression="(= reporting_compliance true)",
            variables=["reporting_compliance"],
            source=ConstraintSource.REGULATORY_RULE,
            source_reference=rule.source_document,
            priority=80,
            metadata={
                "rule_type": "reporting_requirement",
                "original_rule_id": rule.rule_id
            }
        )
        
        constraints.append(constraint)
        return constraints, errors
    
    def _translate_disclosure_rule(self, rule: ExtractedRule) -> Tuple[List[Constraint], List[str]]:
        """Translate disclosure rules."""
        constraints = []
        errors = []
        
        # Similar to reporting, disclosure is often boolean
        constraint = Constraint(
            constraint_id=f"disclose_{rule.rule_id}",
            constraint_type=ConstraintType.BOOLEAN,
            expression="disclosure_compliance = true",
            smt_expression="(= disclosure_compliance true)",
            variables=["disclosure_compliance"],
            source=ConstraintSource.REGULATORY_RULE,
            source_reference=rule.source_document,
            priority=80,
            metadata={
                "rule_type": "disclosure_rule",
                "original_rule_id": rule.rule_id
            }
        )
        
        constraints.append(constraint)
        return constraints, errors
    
    def _generic_translation(self, rule: ExtractedRule) -> Tuple[List[Constraint], List[str]]:
        """Generic translation for unrecognized rule types."""
        constraints = []
        errors = []
        
        # Create a placeholder constraint
        constraint = Constraint(
            constraint_id=f"generic_{rule.rule_id}",
            constraint_type=ConstraintType.BOOLEAN,
            expression="compliance_flag = true",
            smt_expression="(= compliance_flag true)",
            variables=["compliance_flag"],
            source=ConstraintSource.REGULATORY_RULE,
            source_reference=rule.source_document,
            priority=10,
            metadata={
                "rule_type": "generic",
                "original_rule_id": rule.rule_id,
                "needs_manual_review": True
            }
        )
        
        constraints.append(constraint)
        errors.append("Generic translation applied - manual review recommended")
        
        return constraints, errors
    
    def _infer_variable_type(self, var_name: str, constraint: Constraint) -> str:
        """Infer variable type from name and constraint context."""
        var_lower = var_name.lower()
        
        if 'ratio' in var_lower or 'percentage' in var_lower:
            return 'real'
        elif 'amount' in var_lower or 'value' in var_lower or 'exposure' in var_lower:
            return 'real'
        elif 'count' in var_lower or 'number' in var_lower:
            return 'int'
        elif 'compliance' in var_lower or 'flag' in var_lower:
            return 'bool'
        
        # Default to real for numerical variables
        return 'real'
    
    def _calculate_translation_confidence(
        self, 
        rule: ExtractedRule, 
        constraints: List[Constraint],
        errors: List[str],
        warnings: List[str]
    ) -> float:
        """Calculate confidence score for translation."""
        confidence = rule.confidence_score  # Start with extraction confidence
        
        # Reduce confidence for errors
        confidence -= len(errors) * 0.2
        
        # Reduce confidence for warnings
        confidence -= len(warnings) * 0.05
        
        # Boost confidence if constraints were successfully generated
        if constraints:
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def get_translation_statistics(self) -> Dict[str, Any]:
        """Get statistics on translation performance."""
        if not self.translation_history:
            return {"total_translations": 0}
        
        successful = sum(1 for r in self.translation_history if r.success)
        avg_confidence = sum(r.translation_confidence for r in self.translation_history) / len(self.translation_history)
        
        total_constraints = sum(len(r.constraints_generated) for r in self.translation_history)
        total_errors = sum(len(r.errors) for r in self.translation_history)
        total_warnings = sum(len(r.warnings) for r in self.translation_history)
        
        return {
            "translator_id": self.translator_id,
            "total_translations": len(self.translation_history),
            "successful_translations": successful,
            "success_rate": successful / len(self.translation_history),
            "average_confidence": avg_confidence,
            "total_constraints_generated": total_constraints,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "constraints_per_rule": total_constraints / len(self.translation_history)
        }
    
    def export_translation_log(self) -> List[Dict[str, Any]]:
        """Export detailed translation log for audit."""
        return [
            {
                "rule_id": result.rule_id,
                "success": result.success,
                "constraints_count": len(result.constraints_generated),
                "constraint_ids": [c.constraint_id for c in result.constraints_generated],
                "warnings": result.warnings,
                "errors": result.errors,
                "confidence": result.translation_confidence,
                "source_rule_type": result.source_rule.regulation_type.value,
                "timestamp": datetime.now().isoformat()
            }
            for result in self.translation_history
        ]
