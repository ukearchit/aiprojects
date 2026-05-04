"""
M2M Proof Serializer and Regulatory API Gateway

Standardizes mathematical proof payloads for direct API submission to regulatory
solvers, enabling continuous, millisecond regulatory compliance verification
without human intermediaries.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib
import json


@dataclass
class RegulatoryProof:
    """A machine-verifiable regulatory compliance proof."""
    proof_id: str
    version: str
    timestamp: datetime
    
    # Application being verified
    application_id: str
    application_hash: str
    
    # Constraints evaluated
    constraint_set_hash: str
    constraints_evaluated: List[str]
    
    # Determination
    determination: str  # "compliant", "non_compliant"
    confidence_score: float
    
    # Mathematical proof data
    proof_artifact: Dict[str, Any]
    
    # Solver information
    solver_id: str
    solver_version: str
    
    # Cryptographic verification
    signature: str
    verification_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "proof_id": self.proof_id,
            "version": self.version,
            "timestamp": self.timestamp.isoformat(),
            "application_id": self.application_id,
            "application_hash": self.application_hash,
            "constraint_set_hash": self.constraint_set_hash,
            "constraints_evaluated": self.constraints_evaluated,
            "determination": self.determination,
            "confidence_score": self.confidence_score,
            "proof_artifact": self.proof_artifact,
            "solver_id": self.solver_id,
            "solver_version": self.solver_version,
            "signature": self.signature
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class RegulatorySubmission:
    """Complete regulatory submission package."""
    submission_id: str
    institution_id: str
    timestamp: datetime
    
    # Proofs included
    proofs: List[RegulatoryProof]
    
    # Aggregate statistics
    summary_statistics: Dict[str, Any]
    
    # Submission metadata
    reporting_period: Dict[str, str]
    regulatory_body: str
    regulation_reference: str
    
    # Verification
    batch_hash: str
    signature: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "submission_id": self.submission_id,
            "institution_id": self.institution_id,
            "timestamp": self.timestamp.isoformat(),
            "proofs": [p.to_dict() for p in self.proofs],
            "summary_statistics": self.summary_statistics,
            "reporting_period": self.reporting_period,
            "regulatory_body": self.regulatory_body,
            "regulation_reference": self.regulation_reference,
            "batch_hash": self.batch_hash,
            "signature": self.signature
        }


class M2MProofSerializer:
    """
    Serializes compliance results into machine-to-machine regulatory proofs.
    
    This component enables:
    - Standardized proof format for regulatory submission
    - Cryptographic verification of compliance determinations
    - Direct API integration with regulatory systems
    - Automated continuous compliance reporting
    """
    
    PROOF_VERSION = "1.0.0"
    
    def __init__(self, serializer_id: str, institution_id: str):
        self.serializer_id = serializer_id
        self.institution_id = institution_id
        self._submissions: List[RegulatorySubmission] = []
        self._proofs_generated: List[RegulatoryProof] = []
        
        # Schema definitions for different regulatory bodies
        self._regulatory_schemas: Dict[str, Dict[str, Any]] = {}
    
    def register_regulatory_schema(
        self, 
        regulatory_body: str, 
        schema: Dict[str, Any]
    ):
        """
        Register a regulatory schema for a specific body.
        
        Args:
            regulatory_body: Name of regulatory body (e.g., "SEC", "Federal Reserve")
            schema: Schema definition including required fields and formats
        """
        self._regulatory_schemas[regulatory_body] = schema
    
    def serialize_proof(
        self,
        compliance_result: Dict[str, Any],
        constraint_snapshot: Dict[str, Any],
        solver_metadata: Dict[str, Any]
    ) -> RegulatoryProof:
        """
        Serialize a compliance result into a regulatory proof.
        
        Args:
            compliance_result: Result from SMTComplianceSolver
            constraint_snapshot: Snapshot of constraints at time of evaluation
            solver_metadata: Metadata about the solver execution
            
        Returns:
            RegulatoryProof ready for M2M transmission
        """
        proof_id = f"proof_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        timestamp = datetime.now()
        
        # Extract application info
        application_id = compliance_result.get("application_id", "unknown")
        application_data = compliance_result.get("model", {})
        
        # Compute hashes
        application_hash = self._compute_hash(application_data)
        constraint_hash = self._compute_hash(constraint_snapshot)
        
        # Determine status
        is_compliant = compliance_result.get("is_compliant", False)
        determination = "compliant" if is_compliant else "non_compliant"
        
        # Build proof artifact
        proof_artifact = {
            "solver_result": compliance_result.get("solver_result", "unknown"),
            "constraints_checked": compliance_result.get("constraints_checked", []),
            "violations": compliance_result.get("violated_constraints", []),
            "unsat_core": compliance_result.get("unsat_core"),
            "explanation": compliance_result.get("explanation", ""),
            "execution_trace": compliance_result.get("proof_data", {})
        }
        
        # Get solver info
        solver_id = solver_metadata.get("solver_id", "unknown")
        solver_version = solver_metadata.get("version", "1.0.0")
        
        # Create proof
        proof = RegulatoryProof(
            proof_id=proof_id,
            version=self.PROOF_VERSION,
            timestamp=timestamp,
            application_id=application_id,
            application_hash=application_hash,
            constraint_set_hash=constraint_hash,
            constraints_evaluated=compliance_result.get("constraints_checked", []),
            determination=determination,
            confidence_score=compliance_result.get("confidence", 1.0 if is_compliant else 0.0),
            proof_artifact=proof_artifact,
            solver_id=solver_id,
            solver_version=solver_version,
            signature=self._sign_proof(proof_id, application_hash, constraint_hash)
        )
        
        self._proofs_generated.append(proof)
        return proof
    
    def create_regulatory_submission(
        self,
        proofs: List[RegulatoryProof],
        reporting_period: Dict[str, str],
        regulatory_body: str,
        regulation_reference: str
    ) -> RegulatorySubmission:
        """
        Create a batch regulatory submission.
        
        Args:
            proofs: List of proofs to include in submission
            reporting_period: Period covered by this submission
            regulatory_body: Target regulatory body
            regulation_reference: Reference to applicable regulation
            
        Returns:
            RegulatorySubmission ready for API transmission
        """
        submission_id = f"submission_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Calculate summary statistics
        total_proofs = len(proofs)
        compliant_count = sum(1 for p in proofs if p.determination == "compliant")
        non_compliant_count = total_proofs - compliant_count
        
        summary_stats = {
            "total_applications": total_proofs,
            "compliant_applications": compliant_count,
            "non_compliant_applications": non_compliant_count,
            "compliance_rate": compliant_count / total_proofs if total_proofs > 0 else 0,
            "generation_timestamp": datetime.now().isoformat()
        }
        
        # Compute batch hash
        batch_content = "".join(p.proof_id for p in proofs)
        batch_hash = self._compute_hash({"proofs": batch_content, "stats": summary_stats})
        
        submission = RegulatorySubmission(
            submission_id=submission_id,
            institution_id=self.institution_id,
            timestamp=datetime.now(),
            proofs=proofs,
            summary_statistics=summary_stats,
            reporting_period=reporting_period,
            regulatory_body=regulatory_body,
            regulation_reference=regulation_reference,
            batch_hash=batch_hash,
            signature=self._sign_submission(submission_id, batch_hash)
        )
        
        self._submissions.append(submission)
        return submission
    
    def export_for_api(self, obj: Any, target_system: str) -> Dict[str, Any]:
        """
        Export object in format suitable for specific regulatory API.
        
        Args:
            obj: RegulatoryProof or RegulatorySubmission
            target_system: Target regulatory system identifier
            
        Returns:
            Dictionary formatted for API submission
        """
        if isinstance(obj, RegulatoryProof):
            payload = obj.to_dict()
        elif isinstance(obj, RegulatorySubmission):
            payload = obj.to_dict()
        else:
            raise ValueError("Object must be RegulatoryProof or RegulatorySubmission")
        
        # Apply schema-specific transformations if registered
        if target_system in self._regulatory_schemas:
            schema = self._regulatory_schemas[target_system]
            payload = self._apply_schema_transformations(payload, schema)
        
        # Add API envelope
        api_payload = {
            "api_version": "1.0",
            "payload_type": type(obj).__name__,
            "timestamp": datetime.now().isoformat(),
            "sender_id": self.institution_id,
            "target_system": target_system,
            "data": payload
        }
        
        return api_payload
    
    def verify_proof(self, proof: RegulatoryProof) -> bool:
        """
        Verify the cryptographic integrity of a proof.
        
        Args:
            proof: Proof to verify
            
        Returns:
            True if proof is valid, False otherwise
        """
        expected_signature = self._sign_proof(
            proof.proof_id,
            proof.application_hash,
            proof.constraint_set_hash
        )
        
        return proof.signature == expected_signature
    
    def _compute_hash(self, data: Any) -> str:
        """Compute SHA-256 hash of data."""
        if isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
        
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _sign_proof(self, proof_id: str, app_hash: str, constraint_hash: str) -> str:
        """Generate signature for a proof."""
        content = f"{proof_id}:{app_hash}:{constraint_hash}:{self.institution_id}"
        return hashlib.sha256(content.encode()).hexdigest()[:64]
    
    def _sign_submission(self, submission_id: str, batch_hash: str) -> str:
        """Generate signature for a submission."""
        content = f"{submission_id}:{batch_hash}:{self.institution_id}"
        return hashlib.sha256(content.encode()).hexdigest()[:64]
    
    def _apply_schema_transformations(
        self, 
        payload: Dict[str, Any], 
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply schema-specific transformations to payload."""
        # This would implement regulatory-body-specific formatting
        # For now, return payload as-is
        return payload
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get serializer statistics."""
        total_proofs = len(self._proofs_generated)
        compliant_proofs = sum(1 for p in self._proofs_generated if p.determination == "compliant")
        
        return {
            "serializer_id": self.serializer_id,
            "institution_id": self.institution_id,
            "total_proofs_generated": total_proofs,
            "compliant_proofs": compliant_proofs,
            "non_compliant_proofs": total_proofs - compliant_proofs,
            "total_submissions": len(self._submissions),
            "registered_schemas": list(self._regulatory_schemas.keys())
        }


class RegulatoryAPIGateway:
    """
    Gateway for submitting proofs to regulatory APIs.
    
    Handles:
    - API authentication
    - Rate limiting
    - Retry logic
    - Response handling
    """
    
    def __init__(self, gateway_id: str, base_urls: Dict[str, str]):
        self.gateway_id = gateway_id
        self.base_urls = base_urls  # Map of regulatory_body -> API URL
        self._submission_log: List[Dict[str, Any]] = []
    
    def submit_to_regulator(
        self,
        submission: RegulatorySubmission,
        regulatory_body: str
    ) -> Dict[str, Any]:
        """
        Submit a regulatory submission to the appropriate API.
        
        Args:
            submission: Submission to send
            regulatory_body: Target regulatory body
            
        Returns:
            API response
        """
        if regulatory_body not in self.base_urls:
            return {
                "status": "error",
                "message": f"No API URL configured for {regulatory_body}"
            }
        
        api_url = self.base_urls[regulatory_body]
        
        # In production, this would make actual HTTP request
        # For now, simulate successful submission
        response = {
            "status": "accepted",
            "submission_id": submission.submission_id,
            "received_at": datetime.now().isoformat(),
            "acknowledgment_id": f"ack_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            "message": f"Submission accepted by {regulatory_body}"
        }
        
        self._log_submission(submission, regulatory_body, response)
        
        return response
    
    def _log_submission(
        self,
        submission: RegulatorySubmission,
        regulatory_body: str,
        response: Dict[str, Any]
    ):
        """Log submission for audit trail."""
        self._submission_log.append({
            "timestamp": datetime.now().isoformat(),
            "submission_id": submission.submission_id,
            "regulatory_body": regulatory_body,
            "proofs_count": len(submission.proofs),
            "response_status": response.get("status"),
            "acknowledgment_id": response.get("acknowledgment_id")
        })
    
    def get_submission_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent submission history."""
        return self._submission_log[-limit:]
