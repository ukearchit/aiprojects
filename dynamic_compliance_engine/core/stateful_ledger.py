"""
Stateful Portfolio Ledger

Provides real-time connectivity to the institution's live portfolio ledger
to assess dynamic concentration limits and enterprise-wide exposure risks.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json


class AssetClass(Enum):
    """Supported asset classes for portfolio tracking."""
    COMMERCIAL_LOAN = "commercial_loan"
    RESIDENTIAL_MORTGAGE = "residential_mortgage"
    CORPORATE_BOND = "corporate_bond"
    EQUITY = "equity"
    DERIVATIVE = "derivative"
    CASH = "cash"


class RiskTier(Enum):
    """Risk classification tiers."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PortfolioPosition:
    """Represents a single position in the portfolio."""
    position_id: str
    asset_class: AssetClass
    notional_value: float
    risk_tier: RiskTier
    counterparty_id: str
    origination_date: datetime
    maturity_date: Optional[datetime]
    collateral_value: float = 0.0
    sector: str = "general"
    region: str = "global"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def exposure(self) -> float:
        """Calculate net exposure (notional - collateral)."""
        return max(0.0, self.notional_value - self.collateral_value)
    
    @property
    def is_performing(self) -> bool:
        """Check if position is currently performing."""
        if self.maturity_date is None:
            return True
        return datetime.now() < self.maturity_date
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize position to dictionary."""
        return {
            "position_id": self.position_id,
            "asset_class": self.asset_class.value,
            "notional_value": self.notional_value,
            "risk_tier": self.risk_tier.value,
            "counterparty_id": self.counterparty_id,
            "origination_date": self.origination_date.isoformat(),
            "maturity_date": self.maturity_date.isoformat() if self.maturity_date else None,
            "collateral_value": self.collateral_value,
            "sector": self.sector,
            "region": self.region,
            "exposure": self.exposure,
            **self.metadata
        }


@dataclass
class ConcentrationLimit:
    """Defines concentration limits for portfolio management."""
    limit_id: str
    dimension: str  # e.g., "sector", "region", "counterparty", "asset_class"
    dimension_value: str
    limit_type: str  # "percentage" or "absolute"
    threshold: float
    warning_threshold: float
    enabled: bool = True
    
    def check_violation(self, current_value: float, total_portfolio_value: float) -> tuple[bool, str]:
        """
        Check if a value violates the concentration limit.
        
        Returns:
            Tuple of (is_violated, violation_message)
        """
        if not self.enabled:
            return False, ""
        
        if self.limit_type == "percentage":
            actual_percentage = (current_value / total_portfolio_value) * 100 if total_portfolio_value > 0 else 0
            
            if actual_percentage > self.threshold:
                return True, f"Concentration limit violated: {actual_percentage:.2f}% > {self.threshold}% for {self.dimension}={self.dimension_value}"
            elif actual_percentage > self.warning_threshold:
                return False, f"WARNING: Approaching concentration limit: {actual_percentage:.2f}% > {self.warning_threshold}%"
        else:  # absolute
            if current_value > self.threshold:
                return True, f"Absolute limit violated: ${current_value:,.2f} > ${self.threshold:,.2f} for {self.dimension}={self.dimension_value}"
            elif current_value > self.warning_threshold:
                return False, f"WARNING: Approaching absolute limit: ${current_value:,.2f} > ${self.warning_threshold:,.2f}"
        
        return False, ""


@dataclass
class EnterpriseRiskLimit:
    """Enterprise-wide risk limits."""
    limit_id: str
    risk_metric: str  # e.g., "total_exposure", "var_95", "expected_loss"
    threshold: float
    current_value: float = 0.0
    enabled: bool = True
    
    def update_current(self, new_value: float):
        """Update the current metric value."""
        self.current_value = new_value
    
    def check_violation(self) -> tuple[bool, str]:
        """Check if current value violates the limit."""
        if not self.enabled:
            return False, ""
        
        if self.current_value > self.threshold:
            return True, f"Enterprise risk limit violated: {self.risk_metric} = {self.current_value:,.2f} > {self.threshold:,.2f}"
        
        return False, ""


class StatefulPortfolioLedger:
    """
    Real-time portfolio ledger with stateful risk monitoring.
    
    Provides:
    - Live portfolio position tracking
    - Dynamic concentration limit monitoring
    - Enterprise-wide exposure calculation
    - Real-time risk metric updates
    """
    
    def __init__(self, ledger_id: str):
        self.ledger_id = ledger_id
        self.positions: Dict[str, PortfolioPosition] = {}
        self.concentration_limits: List[ConcentrationLimit] = []
        self.enterprise_limits: List[EnterpriseRiskLimit] = []
        self.last_updated: datetime = datetime.now()
        self._total_exposure: float = 0.0
        self._sector_exposures: Dict[str, float] = {}
        self._region_exposures: Dict[str, float] = {}
        self._counterparty_exposures: Dict[str, float] = {}
    
    def add_position(self, position: PortfolioPosition):
        """Add a new position to the ledger."""
        self.positions[position.position_id] = position
        self._update_aggregates(position)
        self.last_updated = datetime.now()
    
    def remove_position(self, position_id: str):
        """Remove a position from the ledger."""
        if position_id in self.positions:
            position = self.positions[position_id]
            self._remove_from_aggregates(position)
            del self.positions[position_id]
            self.last_updated = datetime.now()
    
    def update_position(self, position_id: str, updates: Dict[str, Any]):
        """Update an existing position."""
        if position_id not in self.positions:
            raise ValueError(f"Position {position_id} not found")
        
        position = self.positions[position_id]
        
        # Remove old aggregates before updating
        self._remove_from_aggregates(position)
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(position, key):
                setattr(position, key, value)
        
        # Re-add to aggregates with new values
        self._update_aggregates(position)
        self.last_updated = datetime.now()
    
    def _update_aggregates(self, position: PortfolioPosition):
        """Update aggregate metrics when adding/updating a position."""
        exposure = position.exposure
        self._total_exposure += exposure
        
        # Update sector exposure
        if position.sector not in self._sector_exposures:
            self._sector_exposures[position.sector] = 0.0
        self._sector_exposures[position.sector] += exposure
        
        # Update region exposure
        if position.region not in self._region_exposures:
            self._region_exposures[position.region] = 0.0
        self._region_exposures[position.region] += exposure
        
        # Update counterparty exposure
        if position.counterparty_id not in self._counterparty_exposures:
            self._counterparty_exposures[position.counterparty_id] = 0.0
        self._counterparty_exposures[position.counterparty_id] += exposure
    
    def _remove_from_aggregates(self, position: PortfolioPosition):
        """Remove position from aggregate metrics."""
        exposure = position.exposure
        self._total_exposure -= exposure
        
        if position.sector in self._sector_exposures:
            self._sector_exposures[position.sector] -= exposure
        
        if position.region in self._region_exposures:
            self._region_exposures[position.region] -= exposure
        
        if position.counterparty_id in self._counterparty_exposures:
            self._counterparty_exposures[position.counterparty_id] -= exposure
    
    def add_concentration_limit(self, limit: ConcentrationLimit):
        """Add a concentration limit to monitor."""
        self.concentration_limits.append(limit)
    
    def add_enterprise_limit(self, limit: EnterpriseRiskLimit):
        """Add an enterprise risk limit."""
        self.enterprise_limits.append(limit)
        # Initialize with current value
        if limit.risk_metric == "total_exposure":
            limit.update_current(self._total_exposure)
    
    def get_total_exposure(self) -> float:
        """Get current total portfolio exposure."""
        return self._total_exposure
    
    def get_sector_exposure(self, sector: str) -> float:
        """Get exposure for a specific sector."""
        return self._sector_exposures.get(sector, 0.0)
    
    def get_region_exposure(self, region: str) -> float:
        """Get exposure for a specific region."""
        return self._region_exposures.get(region, 0.0)
    
    def get_counterparty_exposure(self, counterparty_id: str) -> float:
        """Get exposure to a specific counterparty."""
        return self._counterparty_exposures.get(counterparty_id, 0.0)
    
    def check_concentration_limits(self) -> List[tuple[ConcentrationLimit, str]]:
        """
        Check all concentration limits against current portfolio.
        
        Returns:
            List of tuples (limit, violation_message) for violated limits
        """
        violations = []
        
        for limit in self.concentration_limits:
            if limit.dimension == "sector":
                current_value = self.get_sector_exposure(limit.dimension_value)
            elif limit.dimension == "region":
                current_value = self.get_region_exposure(limit.dimension_value)
            elif limit.dimension == "counterparty":
                current_value = self.get_counterparty_exposure(limit.dimension_value)
            elif limit.dimension == "asset_class":
                current_value = sum(
                    p.exposure for p in self.positions.values() 
                    if p.asset_class.value == limit.dimension_value
                )
            else:
                continue
            
            is_violated, message = limit.check_violation(current_value, self._total_exposure)
            if is_violated:
                violations.append((limit, message))
        
        return violations
    
    def check_enterprise_limits(self) -> List[tuple[EnterpriseRiskLimit, str]]:
        """
        Check all enterprise risk limits.
        
        Returns:
            List of tuples (limit, violation_message) for violated limits
        """
        violations = []
        
        # Update enterprise limits with current values
        for limit in self.enterprise_limits:
            if limit.risk_metric == "total_exposure":
                limit.update_current(self._total_exposure)
            # Additional metrics can be added here
        
            is_violated, message = limit.check_violation()
            if is_violated:
                violations.append((limit, message))
        
        return violations
    
    def simulate_new_position(self, position: PortfolioPosition) -> Dict[str, Any]:
        """
        Simulate adding a new position without committing it.
        
        Returns:
            Dictionary with simulation results including potential violations
        """
        # Calculate hypothetical aggregates
        hypothetical_total = self._total_exposure + position.exposure
        hypothetical_sector = self.get_sector_exposure(position.sector) + position.exposure
        hypothetical_region = self.get_region_exposure(position.region) + position.exposure
        hypothetical_counterparty = self.get_counterparty_exposure(position.counterparty_id) + position.exposure
        
        # Check potential violations
        potential_violations = []
        
        for limit in self.concentration_limits:
            if limit.dimension == "sector" and limit.dimension_value == position.sector:
                is_violated, message = limit.check_violation(hypothetical_sector, hypothetical_total)
                if is_violated:
                    potential_violations.append(message)
            elif limit.dimension == "region" and limit.dimension_value == position.region:
                is_violated, message = limit.check_violation(hypothetical_region, hypothetical_total)
                if is_violated:
                    potential_violations.append(message)
            elif limit.dimension == "counterparty" and limit.dimension_value == position.counterparty_id:
                is_violated, message = limit.check_violation(hypothetical_counterparty, hypothetical_total)
                if is_violated:
                    potential_violations.append(message)
        
        for limit in self.enterprise_limits:
            if limit.risk_metric == "total_exposure":
                # Temporarily update and check
                old_value = limit.current_value
                limit.update_current(hypothetical_total)
                is_violated, message = limit.check_violation()
                limit.update_current(old_value)  # Restore
                
                if is_violated:
                    potential_violations.append(message)
        
        return {
            "would_violate": len(potential_violations) > 0,
            "violations": potential_violations,
            "hypothetical_total_exposure": hypothetical_total,
            "position_exposure": position.exposure
        }
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary."""
        return {
            "ledger_id": self.ledger_id,
            "last_updated": self.last_updated.isoformat(),
            "total_positions": len(self.positions),
            "total_exposure": self._total_exposure,
            "sector_breakdown": dict(self._sector_exposures),
            "region_breakdown": dict(self._region_exposures),
            "concentration_violations": [
                msg for _, msg in self.check_concentration_limits()
            ],
            "enterprise_violations": [
                msg for _, msg in self.check_enterprise_limits()
            ]
        }
    
    def export_state_for_solver(self) -> Dict[str, Any]:
        """
        Export current ledger state in format suitable for SMT solver.
        
        This enables stateful portfolio verification by providing the solver
        with real-time constraint context.
        """
        return {
            "ledger_state": {
                "total_exposure": self._total_exposure,
                "sector_exposures": self._sector_exposures,
                "region_exposures": self._region_exposures,
                "counterparty_exposures": self._counterparty_exposures,
            },
            "active_constraints": [
                {
                    "type": "concentration",
                    "dimension": limit.dimension,
                    "value": limit.dimension_value,
                    "threshold": limit.threshold,
                    "limit_type": limit.limit_type,
                }
                for limit in self.concentration_limits if limit.enabled
            ] + [
                {
                    "type": "enterprise",
                    "metric": limit.risk_metric,
                    "threshold": limit.threshold,
                }
                for limit in self.enterprise_limits if limit.enabled
            ],
            "positions_count": len(self.positions)
        }
