import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

import xmlschema

from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class ValidationError:
    def __init__(self, code: str, message: str, element_id: Optional[str] = None):
        self.code = code
        self.message = message
        self.element_id = element_id

    def __str__(self) -> str:
        if self.element_id:
            return f"{self.code}: {self.message} (element: {self.element_id})"
        return f"{self.code}: {self.message}"

    def __repr__(self) -> str:
        return self.__str__()

    def to_dict(self) -> Dict[str, str]:
        result = {"code": self.code, "message": self.message}
        if self.element_id:
            result["element_id"] = self.element_id
        return result


class ValidationResult:
    def __init__(self, is_valid: bool, errors: Optional[List[ValidationError]] = None):
        self.is_valid = is_valid
        self.errors = errors or []

    def add_error(
        self, code: str, message: str, element_id: Optional[str] = None
    ) -> None:
        self.errors.append(ValidationError(code, message, element_id))
        self.is_valid = False


class BPMNValidator:
    """Validates BPMN XML against schema and structural rules."""

    def __init__(self):
        schema_dir = Path(__file__).parent / "schemas"
        bpmn_dir = schema_dir / "bpmn20"

        # Load BPMN schema
        self.bpmn_schema = xmlschema.XMLSchema(
            bpmn_dir / "BPMN20.xsd",
            validation="lax",  # Use lax validation to handle missing imports
            base_url=str(bpmn_dir.absolute()),  # Set base URL for imports
        )

        # Load Pythmata extension schema
        self.extension_schema = xmlschema.XMLSchema(
            schema_dir / "pythmata.xsd", 
            validation="lax"
        )
        
        # Define known validation issues to skip
        self.known_validation_patterns = [
            "tFormalExpression",
            "global xs:simpleType/xs:complexType 'bpmn:tFormalExpression' not found"
        ]

    def validate(self, xml: str) -> ValidationResult:
        """
        Validates a BPMN XML string against the BPMN 2.0 schema and additional rules.

        Args:
            xml: The BPMN XML string to validate

        Returns:
            ValidationResult containing validation status and any errors
        """
        result = ValidationResult(True)

        # Basic XML parsing check
        if not xml.strip():
            result.add_error("EMPTY_XML", "XML content is empty")
            return result

        try:
            # Parse XML first
            try:
                doc = ET.fromstring(xml.strip())
            except ET.ParseError as e:
                result.add_error("XML_PARSE_ERROR", str(e))
                return result

            # Define namespaces for validation
            namespaces = {
                'bpmn': "http://www.omg.org/spec/BPMN/20100524/MODEL",
                'xsi': "http://www.w3.org/2001/XMLSchema-instance"
            }
            
            # Validate against BPMN schema with relaxed extension validation
            validation_errors = []
            for error in self.bpmn_schema.iter_errors(doc, namespaces=namespaces):
                # Skip errors related to extension elements
                if "extensionElements" not in str(error):
                    # Check if this is a known validation issue to skip
                    should_skip = False
                    for pattern in self.known_validation_patterns:
                        if pattern in str(error):
                            logger.debug(f"Skipping known validation issue: {error}")
                            should_skip = True
                            break
                    
                    if not should_skip:
                        validation_errors.append(error)

            if validation_errors:
                for error in validation_errors:
                    result.add_error("SCHEMA_ERROR", str(error))
                return result

            # Validate extension elements separately
            for task in doc.findall(".//{*}serviceTask"):
                extensions = task.find("{*}extensionElements")
                if extensions is not None:
                    for config in extensions.findall(".//{*}taskConfig"):
                        try:
                            # Create a temporary XML document with just the extension
                            extension_doc = ET.Element(
                                "{http://pythmata.org/schema/1.0/bpmn}taskConfig"
                            )
                            extension_doc.extend(config)
                            self.extension_schema.validate(extension_doc)
                        except xmlschema.XMLSchemaValidationError as e:
                            result.add_error(
                                "EXTENSION_ERROR",
                                f"Invalid extension in task {task.get('id')}: {str(e)}",
                            )
                            return result

            # Parse XML for additional validation
            try:
                doc = ET.fromstring(xml.strip())
            except ET.ParseError as e:
                result.add_error("XML_PARSE_ERROR", str(e))
                return result

            # Validate ID uniqueness
            ids = {}
            for elem in doc.findall(".//*[@id]"):
                elem_id = elem.get("id")
                if elem_id in ids:
                    result.add_error(
                        "DUPLICATE_ID", f"Duplicate ID '{elem_id}' found", elem_id
                    )
                ids[elem_id] = elem

            # Validate sequence flows
            for process in doc.findall(".//{*}process"):
                if not process.get("id"):
                    result.add_error(
                        "MISSING_ATTRIBUTE",
                        "Process element missing required 'id' attribute",
                    )

                # Get all flow nodes
                nodes = (
                    process.findall(".//{*}startEvent")
                    + process.findall(".//{*}task")
                    + process.findall(".//{*}endEvent")
                )

                # Get all sequence flows
                flows = process.findall(".//{*}sequenceFlow")

                # Check if nodes are connected
                if nodes and not flows:
                    result.add_error(
                        "INVALID_STRUCTURE",
                        "Process contains nodes but no sequence flows",
                    )

                # Validate flow references
                for flow in flows:
                    source_ref = flow.get("sourceRef")
                    target_ref = flow.get("targetRef")

                    if not source_ref or not target_ref:
                        result.add_error(
                            "INVALID_FLOW",
                            f"Sequence flow {flow.get('id')} missing source or target reference",
                        )
                        continue

                    if source_ref not in ids or target_ref not in ids:
                        result.add_error(
                            "INVALID_REFERENCE",
                            f"Sequence flow {flow.get('id')} references non-existent node",
                        )

        except xmlschema.XMLSchemaValidationError as e:
            result.add_error("SCHEMA_ERROR", str(e))
        except ET.ParseError as e:
            result.add_error("XML_PARSE_ERROR", str(e))
        except Exception as e:
            result.add_error("VALIDATION_ERROR", str(e))

        return result
