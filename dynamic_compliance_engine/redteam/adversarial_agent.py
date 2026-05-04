"""
Adversarial Red Team Agent

Deploys adversarial agents to synthetically attack and identify logical loopholes
in proposed underwriting guidelines before deployment.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import random


class AttackType(Enum):
    """Types of adversarial attacks."""
    CONSTRAINT_BOUNDARY = "constraint_boundary"  # Test edge cases at constraint boundaries
    PARAMETER_EXPLOITATION = "parameter_exploitation"  # Exploit parameter combinations
    LOGICAL_LOOPHOLE = "logical_loophole"  # Find logical gaps in rules
    ADVERSARIAL_EXAMPLE = "adversarial_example"  # Craft inputs to bypass detection
    COMPLEXITY_ATTACK = "complexity_attack"  # Overwhelm with complex scenarios


@dataclass
class AdversarialTest:
    """A single adversarial test case."""
    test_id: str
    attack_type: AttackType
    description: str
    
    # Generated test input
    test_input: Dict[str, Any]
    
    # Expected behavior
    expected_result: str
    
    # Actual result from testing
    actual_result: Optional[str] = None
    
    # Whether the attack succeeded (found a vulnerability)
    attack_succeeded: bool = False
    
    # Vulnerability details if found
    vulnerability_description: Optional[str] = None
    
    # Severity rating
    severity: str = "unknown"  # "critical", "high", "medium", "low"
    
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RedTeamReport:
    """Comprehensive report from red team exercise."""
    report_id: str
    target_system: str
    timestamp: datetime
    
    # Test summary
    total_tests: int
    successful_attacks: int
    failed_attacks: int
    
    # Vulnerabilities found
    vulnerabilities: List[Dict[str, Any]]
    
    # Recommendations
    recommendations: List[str]
    
    # Overall risk assessment
    risk_level: str  # "critical", "high", "medium", "low"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "target_system": self.target_system,
            "timestamp": self.timestamp.isoformat(),
            "summary": {
                "total_tests": self.total_tests,
                "successful_attacks": self.successful_attacks,
                "failed_attacks": self.failed_attacks,
                "success_rate": self.successful_attacks / self.total_tests if self.total_tests > 0 else 0
            },
            "vulnerabilities": self.vulnerabilities,
            "recommendations": self.recommendations,
            "risk_level": self.risk_level
        }


class AdversarialRedTeamAgent:
    """
    Automated red team agent for testing compliance systems.
    
    This component:
    - Generates adversarial test cases
    - Attempts to find loopholes in constraint logic
    - Identifies boundary conditions that cause failures
    - Produces actionable vulnerability reports
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.test_history: List[AdversarialTest] = []
        self._attack_strategies: Dict[AttackType, callable] = self._initialize_strategies()
        self._constraint_knowledge: Dict[str, Dict[str, Any]] = {}
    
    def _initialize_strategies(self) -> Dict[AttackType, callable]:
        """Initialize attack generation strategies."""
        return {
            AttackType.CONSTRAINT_BOUNDARY: self._generate_boundary_tests,
            AttackType.PARAMETER_EXPLOITATION: self._generate_parameter_tests,
            AttackType.LOGICAL_LOOPHOLE: self._generate_loophole_tests,
            AttackType.ADVERSARIAL_EXAMPLE: self._generate_adversarial_examples,
            AttackType.COMPLEXITY_ATTACK: self._generate_complexity_tests,
        }
    
    def register_constraint_schema(self, constraint_id: str, schema: Dict[str, Any]):
        """
        Register knowledge about a constraint for targeted testing.
        
        Args:
            constraint_id: ID of the constraint
            schema: Constraint schema including type, bounds, variables
        """
        self._constraint_knowledge[constraint_id] = schema
    
    def run_red_team_exercise(
        self,
        target_constraints: List[str],
        num_tests_per_type: int = 10,
        compliance_checker: callable = None
    ) -> RedTeamReport:
        """
        Run comprehensive red team exercise against target constraints.
        
        Args:
            target_constraints: List of constraint IDs to test
            num_tests_per_type: Number of tests per attack type
            compliance_checker: Function to evaluate test inputs
            
        Returns:
            RedTeamReport with findings
        """
        report_id = f"redteam_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        all_tests = []
        vulnerabilities = []
        
        # Generate tests for each attack type
        for attack_type, strategy_func in self._attack_strategies.items():
            tests = strategy_func(target_constraints, num_tests_per_type)
            all_tests.extend(tests)
        
        # Execute tests if compliance checker provided
        if compliance_checker:
            for test in all_tests:
                try:
                    result = compliance_checker(test.test_input)
                    test.actual_result = result.get("status", "unknown")
                    
                    # Determine if attack succeeded
                    if self._evaluate_attack_success(test, result):
                        test.attack_succeeded = True
                        test.vulnerability_description = self._describe_vulnerability(test, result)
                        test.severity = self._assess_severity(test, result)
                        
                        vulnerabilities.append({
                            "test_id": test.test_id,
                            "attack_type": test.attack_type.value,
                            "description": test.vulnerability_description,
                            "severity": test.severity,
                            "test_input": test.test_input,
                            "actual_result": test.actual_result
                        })
                except Exception as e:
                    test.actual_result = f"error: {str(e)}"
                    test.attack_succeeded = True
                    test.severity = "high"
                
                self.test_history.append(test)
        
        # Calculate statistics
        total_tests = len(all_tests)
        successful = sum(1 for t in all_tests if t.attack_succeeded)
        failed = total_tests - successful
        
        # Generate recommendations
        recommendations = self._generate_recommendations(vulnerabilities)
        
        # Assess overall risk
        risk_level = self._assess_overall_risk(successful, total_tests, vulnerabilities)
        
        report = RedTeamReport(
            report_id=report_id,
            target_system="compliance_engine",
            timestamp=datetime.now(),
            total_tests=total_tests,
            successful_attacks=successful,
            failed_attacks=failed,
            vulnerabilities=vulnerabilities,
            recommendations=recommendations,
            risk_level=risk_level
        )
        
        return report
    
    def _generate_boundary_tests(
        self, 
        constraints: List[str], 
        count: int
    ) -> List[AdversarialTest]:
        """Generate tests targeting constraint boundaries."""
        tests = []
        
        for i in range(count):
            constraint_id = random.choice(constraints) if constraints else "unknown"
            schema = self._constraint_knowledge.get(constraint_id, {})
            
            # Generate values at/around boundaries
            threshold = schema.get("threshold", 100)
            
            test_input = {
                "constraint_target": constraint_id,
                "test_value": threshold + random.uniform(-0.01, 0.01) * threshold,
                "boundary_type": random.choice(["just_below", "at", "just_above"])
            }
            
            test = AdversarialTest(
                test_id=f"boundary_test_{i}_{datetime.now().strftime('%H%M%S%f')}",
                attack_type=AttackType.CONSTRAINT_BOUNDARY,
                description=f"Testing boundary condition for {constraint_id}",
                test_input=test_input,
                expected_result="consistent_boundary_handling"
            )
            
            tests.append(test)
        
        return tests
    
    def _generate_parameter_tests(
        self,
        constraints: List[str],
        count: int
    ) -> List[AdversarialTest]:
        """Generate tests exploiting parameter combinations."""
        tests = []
        
        for i in range(count):
            # Generate extreme parameter combinations
            test_input = {
                "loan_amount": random.choice([0, 1e6, 1e9, -1000]),
                "interest_rate": random.choice([0, 0.001, 0.5, 1.0, -0.1]),
                "ltv_ratio": random.choice([0, 0.5, 1.0, 1.5, 2.0]),
                "debt_to_income": random.choice([0, 0.3, 1.0, 5.0]),
                "collateral_value": random.choice([0, 1e6, -1000])
            }
            
            test = AdversarialTest(
                test_id=f"param_test_{i}_{datetime.now().strftime('%H%M%S%f')}",
                attack_type=AttackType.PARAMETER_EXPLOITATION,
                description=f"Testing extreme parameter combination {i}",
                test_input=test_input,
                expected_result="graceful_handling_of_extremes"
            )
            
            tests.append(test)
        
        return tests
    
    def _generate_loophole_tests(
        self,
        constraints: List[str],
        count: int
    ) -> List[AdversarialTest]:
        """Generate tests to find logical loopholes."""
        tests = []
        
        loophole_patterns = [
            # Zero-value exploitation
            {"loan_amount": 0, "expected_behavior": "should_reject_or_flag"},
            # Rounding exploitation
            {"loan_amount": 999999.99, "threshold": 1000000},
            # Multiple small transactions (structuring)
            {"transaction_count": 10, "individual_amount": 9000, "total": 90000},
            # Conflicting constraint exploitation
            {"exploit_conflict": True, "constraint_a": "high", "constraint_b": "low"},
        ]
        
        for i in range(count):
            pattern = random.choice(loophole_patterns)
            
            test = AdversarialTest(
                test_id=f"loophole_test_{i}_{datetime.now().strftime('%H%M%S%f')}",
                attack_type=AttackType.LOGICAL_LOOPHOLE,
                description=f"Testing logical loophole pattern",
                test_input=pattern,
                expected_result="no_logical_exploitation_possible"
            )
            
            tests.append(test)
        
        return tests
    
    def _generate_adversarial_examples(
        self,
        constraints: List[str],
        count: int
    ) -> List[AdversarialTest]:
        """Generate crafted inputs designed to bypass detection."""
        tests = []
        
        for i in range(count):
            # Create inputs that are technically compliant but violate spirit
            test_input = {
                "structure_type": "technically_compliant",
                "risk_indicators": "minimized",
                "documentation": "minimal_but_sufficient",
                "adversarial_intent": True
            }
            
            test = AdversarialTest(
                test_id=f"adversarial_{i}_{datetime.now().strftime('%H%M%S%f')}",
                attack_type=AttackType.ADVERSARIAL_EXAMPLE,
                description=f"Adversarial example attempting to bypass detection",
                test_input=test_input,
                expected_result="detection_of_adversarial_intent"
            )
            
            tests.append(test)
        
        return tests
    
    def _generate_complexity_tests(
        self,
        constraints: List[str],
        count: int
    ) -> List[AdversarialTest]:
        """Generate overly complex scenarios to stress the system."""
        tests = []
        
        for i in range(count):
            # Create complex multi-entity structures
            test_input = {
                "entity_count": random.randint(10, 100),
                "relationship_depth": random.randint(5, 20),
                "transaction_layers": random.randint(3, 10),
                "jurisdictions": random.sample(["US", "UK", "EU", "CA", "AU"], k=random.randint(2, 5))
            }
            
            test = AdversarialTest(
                test_id=f"complexity_test_{i}_{datetime.now().strftime('%H%M%S%f')}",
                attack_type=AttackType.COMPLEXITY_ATTACK,
                description=f"Complexity attack with {test_input['entity_count']} entities",
                test_input=test_input,
                expected_result="handles_complexity_without_failure"
            )
            
            tests.append(test)
        
        return tests
    
    def _evaluate_attack_success(self, test: AdversarialTest, result: Dict) -> bool:
        """Evaluate whether an attack succeeded."""
        # Check for error states
        if "error" in test.actual_result.lower() if test.actual_result else False:
            return True
        
        # Check for unexpected behavior
        if result.get("status") == "unexpected":
            return True
        
        # Check for boundary inconsistencies
        if test.attack_type == AttackType.CONSTRAINT_BOUNDARY:
            if result.get("boundary_handled") == False:
                return True
        
        return False
    
    def _describe_vulnerability(self, test: AdversarialTest, result: Dict) -> str:
        """Generate description of discovered vulnerability."""
        return f"Vulnerability found via {test.attack_type.value}: {test.description}"
    
    def _assess_severity(self, test: AdversarialTest, result: Dict) -> str:
        """Assess severity of discovered vulnerability."""
        # Default severity based on attack type
        severity_map = {
            AttackType.LOGICAL_LOOPHOLE: "high",
            AttackType.ADVERSARIAL_EXAMPLE: "high",
            AttackType.CONSTRAINT_BOUNDARY: "medium",
            AttackType.PARAMETER_EXPLOITATION: "medium",
            AttackType.COMPLEXITY_ATTACK: "low"
        }
        
        return severity_map.get(test.attack_type, "medium")
    
    def _generate_recommendations(self, vulnerabilities: List[Dict]) -> List[str]:
        """Generate remediation recommendations."""
        recommendations = []
        
        if not vulnerabilities:
            return ["No critical vulnerabilities found. Continue regular monitoring."]
        
        # Analyze vulnerability patterns
        types_found = set(v["attack_type"] for v in vulnerabilities)
        
        if "logical_loophole" in types_found:
            recommendations.append("Review and strengthen logical consistency of constraint rules")
        
        if "constraint_boundary" in types_found:
            recommendations.append("Add explicit boundary handling and edge case tests")
        
        if "parameter_exploitation" in types_found:
            recommendations.append("Implement input validation and range checking")
        
        if "adversarial_example" in types_found:
            recommendations.append("Deploy adversarial detection mechanisms")
        
        if "complexity_attack" in types_found:
            recommendations.append("Set complexity limits and implement graceful degradation")
        
        recommendations.append("Schedule regular red team exercises")
        recommendations.append("Implement continuous monitoring for newly discovered attack vectors")
        
        return recommendations
    
    def _assess_overall_risk(
        self,
        successful: int,
        total: int,
        vulnerabilities: List[Dict]
    ) -> str:
        """Assess overall risk level."""
        if total == 0:
            return "unknown"
        
        success_rate = successful / total
        
        # Check for critical vulnerabilities
        critical_count = sum(1 for v in vulnerabilities if v.get("severity") == "critical")
        high_count = sum(1 for v in vulnerabilities if v.get("severity") == "high")
        
        if critical_count > 0 or success_rate > 0.5:
            return "critical"
        elif high_count > 2 or success_rate > 0.3:
            return "high"
        elif successful > 0:
            return "medium"
        else:
            return "low"
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get red team statistics."""
        if not self.test_history:
            return {"total_tests": 0}
        
        attack_counts = {}
        success_counts = {}
        
        for test in self.test_history:
            attack_type = test.attack_type.value
            attack_counts[attack_type] = attack_counts.get(attack_type, 0) + 1
            if test.attack_succeeded:
                success_counts[attack_type] = success_counts.get(attack_type, 0) + 1
        
        return {
            "agent_id": self.agent_id,
            "total_tests_run": len(self.test_history),
            "total_successful_attacks": sum(1 for t in self.test_history if t.attack_succeeded),
            "by_attack_type": attack_counts,
            "success_rate_by_type": {
                t: success_counts.get(t, 0) / attack_counts[t] if attack_counts[t] > 0 else 0
                for t in attack_counts
            }
        }
