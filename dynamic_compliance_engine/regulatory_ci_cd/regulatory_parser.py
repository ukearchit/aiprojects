"""
Regulatory Parser

Parses regulatory documents (SEC bulletins, Basel III amendments, etc.)
and extracts structured rule representations for translation to solver constraints.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import json


class RegulationType(Enum):
    """Types of regulations supported."""
    CAPITAL_REQUIREMENT = "capital_requirement"
    CONCENTRATION_LIMIT = "concentration_limit"
    LIQUIDITY_RULE = "liquidity_rule"
    REPORTING_REQUIREMENT = "reporting_requirement"
    RISK_WEIGHT_RULE = "risk_weight_rule"
    LENDING_LIMIT = "lending_limit"
    DISCLOSURE_RULE = "disclosure_rule"


class RegulatoryBody(Enum):
    """Regulatory bodies that issue rules."""
    SEC = "SEC"
    FEDERAL_RESERVE = "Federal Reserve"
    OCC = "OCC"
    FDIC = "FDIC"
    BASEL_COMMITTEE = "Basel Committee"
    CFPB = "CFPB"
    STATE_REGULATOR = "State Regulator"


@dataclass
class ExtractedRule:
    """Represents a rule extracted from regulatory text."""
    rule_id: str
    title: str
    description: str
    regulation_type: RegulationType
    regulatory_body: RegulatoryBody
    source_document: str
    section_reference: str
    effective_date: Optional[datetime]
    expiration_date: Optional[datetime]
    
    # Rule parameters extracted from text
    parameters: Dict[str, Any]
    
    # Natural language conditions
    conditions: List[str]
    
    # Confidence score from extraction (0-1)
    confidence_score: float
    
    # Raw text snippet
    raw_text: str
    
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegulatoryDocument:
    """Represents a parsed regulatory document."""
    document_id: str
    title: str
    regulatory_body: RegulatoryBody
    publication_date: datetime
    effective_date: Optional[datetime]
    document_type: str  # "bulletin", "amendment", "rule", "guidance"
    url: Optional[str]
    
    # Extracted rules from this document
    extracted_rules: List[ExtractedRule]
    
    # Full text content
    content: str
    
    # Parsing metadata
    parsing_timestamp: datetime = field(default_factory=datetime.now)
    parser_version: str = "1.0.0"


class RegulatoryParser:
    """
    Parses regulatory documents and extracts structured rules.
    
    This component handles:
    - Document ingestion from various sources (PDF, HTML, XML, plain text)
    - Rule extraction using pattern matching and NLP
    - Parameter identification from regulatory text
    - Confidence scoring for extracted rules
    """
    
    def __init__(self, parser_id: str):
        self.parser_id = parser_id
        self.parsed_documents: Dict[str, RegulatoryDocument] = {}
        self.extracted_rules: Dict[str, ExtractedRule] = {}
        
        # Pattern definitions for rule extraction
        self._patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Initialize regex patterns for rule extraction."""
        patterns = {
            # Capital requirements
            "capital_ratio": [
                re.compile(r'capital\s+ratio\s+(?:of|shall\s+be|must\s+be)\s*([\d.]+)%', re.IGNORECASE),
                re.compile(r'maintain\s+(?:a\s+)?(?:minimum\s+)?capital\s+(?:ratio)\s+(?:of\s+)?([\d.]+)%', re.IGNORECASE),
            ],
            # Concentration limits
            "concentration_limit": [
                re.compile(r'(?:concentration|exposure)\s+limit\s+(?:of|shall\s+not\s+exceed)\s*([\d.]+)%', re.IGNORECASE),
                re.compile(r'(?:aggregate\s+)?(?:loans|exposures)\s+to\s+(?:a\s+)?single\s+(?:borrower|counterparty)\s+(?:shall\s+not\s+)?exceed\s+([\d.]+)%', re.IGNORECASE),
            ],
            # Lending limits
            "lending_limit": [
                re.compile(r'(?:lending|loan)\s+limit\s+(?:of|shall\s+not\s+exceed)\s*\$?([\d.,]+)', re.IGNORECASE),
                re.compile(r'maximum\s+(?:loan|exposure)\s+(?:amount)?\s+(?:of|shall\s+be)\s*\$?([\d.,]+)', re.IGNORECASE),
            ],
            # Liquidity requirements
            "liquidity_ratio": [
                re.compile(r'liquidity\s+coverage\s+ratio\s+(?:of|shall\s+be)\s*([\d.]+)%', re.IGNORECASE),
                re.compile(r'LCR\s+(?:of|shall\s+be)\s*([\d.]+)%', re.IGNORECASE),
            ],
            # Effective dates
            "effective_date": [
                re.compile(r'effective\s+(?:date)?\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})', re.IGNORECASE),
                re.compile(r'shall\s+take\s+effect\s+on\s+(\w+\s+\d{1,2},?\s+\d{4})', re.IGNORECASE),
            ],
        }
        return patterns
    
    def parse_document(self, content: str, metadata: Dict[str, Any]) -> RegulatoryDocument:
        """
        Parse a regulatory document and extract rules.
        
        Args:
            content: Full text content of the document
            metadata: Document metadata including title, body, dates, etc.
            
        Returns:
            RegulatoryDocument with extracted rules
        """
        doc_id = metadata.get("document_id", f"doc_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        
        # Create document object
        document = RegulatoryDocument(
            document_id=doc_id,
            title=metadata.get("title", "Untitled Document"),
            regulatory_body=RegulatoryBody(metadata.get("regulatory_body", "SEC")),
            publication_date=datetime.fromisoformat(metadata["publication_date"]) if "publication_date" in metadata else datetime.now(),
            effective_date=datetime.fromisoformat(metadata["effective_date"]) if "effective_date" in metadata else None,
            document_type=metadata.get("document_type", "bulletin"),
            url=metadata.get("url"),
            extracted_rules=[],
            content=content
        )
        
        # Extract rules from content
        extracted_rules = self._extract_rules(content, document)
        document.extracted_rules = extracted_rules
        
        # Store parsed document
        self.parsed_documents[doc_id] = document
        
        # Index extracted rules
        for rule in extracted_rules:
            self.extracted_rules[rule.rule_id] = rule
        
        return document
    
    def _extract_rules(self, content: str, document: RegulatoryDocument) -> List[ExtractedRule]:
        """Extract individual rules from document content."""
        rules = []
        
        # Split content into sections
        sections = self._split_into_sections(content)
        
        rule_counter = 0
        for section_title, section_content in sections:
            # Try to identify rule type and extract parameters
            rule_candidates = self._identify_rule_candidates(section_content)
            
            for candidate in rule_candidates:
                rule_counter += 1
                rule_id = f"{document.document_id}_rule_{rule_counter:03d}"
                
                rule = ExtractedRule(
                    rule_id=rule_id,
                    title=candidate.get("title", f"Rule {rule_counter}"),
                    description=candidate.get("description", ""),
                    regulation_type=candidate.get("regulation_type", RegulationType.REPORTING_REQUIREMENT),
                    regulatory_body=document.regulatory_body,
                    source_document=document.document_id,
                    section_reference=section_title,
                    effective_date=document.effective_date,
                    expiration_date=None,
                    parameters=candidate.get("parameters", {}),
                    conditions=candidate.get("conditions", []),
                    confidence_score=candidate.get("confidence", 0.5),
                    raw_text=candidate.get("raw_text", "")
                )
                
                rules.append(rule)
        
        return rules
    
    def _split_into_sections(self, content: str) -> List[Tuple[str, str]]:
        """Split document content into sections."""
        sections = []
        
        # Simple section splitting based on numbered headers
        # More sophisticated parsing would use document structure
        section_pattern = re.compile(r'(?:Section|Article|Part)\s+([A-Z0-9\.]+)[:\s]+([^\n]+)', re.IGNORECASE)
        
        matches = list(section_pattern.finditer(content))
        
        if not matches:
            # If no sections found, treat entire content as one section
            return [("General", content)]
        
        for i, match in enumerate(matches):
            section_num = match.group(1)
            section_title = match.group(2).strip()
            
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            
            section_content = content[start_pos:end_pos].strip()
            sections.append((f"Section {section_num}: {section_title}", section_content))
        
        return sections
    
    def _identify_rule_candidates(self, section_content: str) -> List[Dict[str, Any]]:
        """Identify potential rules within a section."""
        candidates = []
        
        # Look for mandatory language
        mandatory_patterns = [
            r'(?:shall|must|required|mandatory|compulsory)[^\n]{10,200}',
            r'(?:no\s+(?:entity|institution|bank|company))[^\n]{10,200}(?:may|shall)',
            r'(?:it\s+is\s+unlawful)[^\n]{10,200}',
        ]
        
        for pattern in mandatory_patterns:
            matches = re.finditer(pattern, section_content, re.IGNORECASE)
            for match in matches:
                rule_text = match.group(0).strip()
                
                # Extract parameters from rule text
                parameters = self._extract_parameters(rule_text)
                
                # Determine regulation type
                reg_type = self._classify_regulation_type(rule_text, parameters)
                
                # Extract conditions
                conditions = self._extract_conditions(rule_text)
                
                candidates.append({
                    "title": self._generate_rule_title(rule_text),
                    "description": rule_text[:200],
                    "regulation_type": reg_type,
                    "parameters": parameters,
                    "conditions": conditions,
                    "confidence": self._calculate_confidence(rule_text, parameters),
                    "raw_text": rule_text
                })
        
        return candidates
    
    def _extract_parameters(self, text: str) -> Dict[str, Any]:
        """Extract numerical and categorical parameters from rule text."""
        parameters = {}
        
        # Extract percentages
        pct_matches = re.findall(r'([\d.]+)\s*%', text)
        if pct_matches:
            parameters['percentages'] = [float(p) for p in pct_matches]
        
        # Extract monetary values
        money_matches = re.findall(r'\$([\d,]+(?:\.\d+)?)', text)
        if money_matches:
            parameters['monetary_values'] = [float(m.replace(',', '')) for m in money_matches]
        
        # Extract time periods
        time_matches = re.findall(r'(\d+)\s*(days?|months?|years?|quarters?)', text, re.IGNORECASE)
        if time_matches:
            parameters['time_periods'] = [
                {"value": int(t[0]), "unit": t[1].lower()} 
                for t in time_matches
            ]
        
        # Apply specific patterns
        for pattern_name, patterns in self._patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    parameters[pattern_name] = match.group(1)
        
        return parameters
    
    def _classify_regulation_type(self, text: str, parameters: Dict[str, Any]) -> RegulationType:
        """Classify the type of regulation based on text and parameters."""
        text_lower = text.lower()
        
        if any(kw in text_lower for kw in ['capital', 'tier 1', 'basel']):
            return RegulationType.CAPITAL_REQUIREMENT
        elif any(kw in text_lower for kw in ['concentration', 'exposure limit', 'single borrower']):
            return RegulationType.CONCENTRATION_LIMIT
        elif any(kw in text_lower for kw in ['liquidity', 'LCR', 'NSFR']):
            return RegulationType.LIQUIDITY_RULE
        elif any(kw in text_lower for kw in ['report', 'disclose', 'filing']):
            return RegulationType.REPORTING_REQUIREMENT
        elif any(kw in text_lower for kw in ['risk weight', 'RWA']):
            return RegulationType.RISK_WEIGHT_RULE
        elif any(kw in text_lower for kw in ['lending limit', 'loan limit', 'maximum loan']):
            return RegulationType.LENDING_LIMIT
        
        return RegulationType.DISCLOSURE_RULE
    
    def _extract_conditions(self, text: str) -> List[str]:
        """Extract conditional clauses from rule text."""
        conditions = []
        
        # Look for IF/WHEN clauses
        condition_patterns = [
            r'(?:if|when|where|in\s+case\s+of|provided\s+that)[^,;]{10,100}',
            r'(?:subject\s+to|except\s+(?:where|if|when))[^,;]{10,100}',
        ]
        
        for pattern in condition_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            conditions.extend([m.strip() for m in matches])
        
        return conditions
    
    def _generate_rule_title(self, text: str) -> str:
        """Generate a concise title for a rule."""
        # Take first meaningful clause
        words = text.split()[:10]
        title = ' '.join(words)
        
        # Truncate if too long
        if len(title) > 80:
            title = title[:77] + "..."
        
        return title
    
    def _calculate_confidence(self, text: str, parameters: Dict[str, Any]) -> float:
        """Calculate confidence score for extracted rule."""
        confidence = 0.5  # Base confidence
        
        # Increase confidence for rules with clear parameters
        if parameters:
            confidence += 0.2
        
        # Increase confidence for rules with mandatory language
        if re.search(r'(shall|must|required)', text, re.IGNORECASE):
            confidence += 0.15
        
        # Increase confidence for rules with specific numbers
        if 'percentages' in parameters or 'monetary_values' in parameters:
            confidence += 0.15
        
        return min(confidence, 1.0)
    
    def get_rules_by_type(self, reg_type: RegulationType) -> List[ExtractedRule]:
        """Get all extracted rules of a specific type."""
        return [r for r in self.extracted_rules.values() if r.regulation_type == reg_type]
    
    def get_rules_by_body(self, body: RegulatoryBody) -> List[ExtractedRule]:
        """Get all rules from a specific regulatory body."""
        return [r for r in self.extracted_rules.values() if r.regulatory_body == body]
    
    def get_high_confidence_rules(self, threshold: float = 0.8) -> List[ExtractedRule]:
        """Get rules with confidence score above threshold."""
        return [r for r in self.extracted_rules.values() if r.confidence_score >= threshold]
    
    def export_rules_json(self) -> str:
        """Export all extracted rules as JSON."""
        return json.dumps([
            {
                "rule_id": r.rule_id,
                "title": r.title,
                "description": r.description,
                "regulation_type": r.regulation_type.value,
                "regulatory_body": r.regulatory_body.value,
                "source_document": r.source_document,
                "section_reference": r.section_reference,
                "effective_date": r.effective_date.isoformat() if r.effective_date else None,
                "parameters": r.parameters,
                "conditions": r.conditions,
                "confidence_score": r.confidence_score,
                "raw_text": r.raw_text
            }
            for r in self.extracted_rules.values()
        ], indent=2)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get parser statistics."""
        type_counts = {}
        for rule in self.extracted_rules.values():
            reg_type = rule.regulation_type.value
            type_counts[reg_type] = type_counts.get(reg_type, 0) + 1
        
        return {
            "parser_id": self.parser_id,
            "documents_parsed": len(self.parsed_documents),
            "rules_extracted": len(self.extracted_rules),
            "by_regulation_type": type_counts,
            "high_confidence_rules": len(self.get_high_confidence_rules(0.8)),
            "average_confidence": sum(r.confidence_score for r in self.extracted_rules.values()) / len(self.extracted_rules) if self.extracted_rules else 0
        }
