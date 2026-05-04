"""
Dynamic Neuro-Symbolic Compliance Engine

This module transforms static compliance checking into an active, generative 
regulatory intelligence engine supporting:
- Automated Regulatory CI/CD
- Stateful Portfolio Verification  
- Compliant Solution Synthesis
- Automated Red-Teaming
- Machine-to-Machine Regulation
"""

__version__ = "1.0.0"
__author__ = "Regulatory Intelligence Team"

from .core.stateful_ledger import StatefulPortfolioLedger
from .core.constraint_manager import DynamicConstraintManager
from .regulatory_ci_cd.regulatory_parser import RegulatoryParser
from .regulatory_ci_cd.rule_translator import RuleTranslator
from .solver.smt_solver import SMTComplianceSolver
from .solver.unsat_core import UnsatisfiableCoreAnalyzer
from .synthesis.solution_synthesizer import CompliantSolutionSynthesizer
from .redteam.adversarial_agent import AdversarialRedTeamAgent
from .m2m.proof_serializer import M2MProofSerializer, RegulatoryAPIGateway

__all__ = [
    # Core Components
    "StatefulPortfolioLedger",
    "DynamicConstraintManager",
    
    # Regulatory CI/CD
    "RegulatoryParser",
    "RuleTranslator",
    
    # Solver Engine
    "SMTComplianceSolver",
    "UnsatisfiableCoreAnalyzer",
    
    # Solution Synthesis
    "CompliantSolutionSynthesizer",
    
    # Red Teaming
    "AdversarialRedTeamAgent",
    
    # M2M Regulation
    "M2MProofSerializer",
    "RegulatoryAPIGateway",
]