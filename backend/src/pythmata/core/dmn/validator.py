import xml.etree.ElementTree as ET
import xmlschema
from pathlib import Path


class DMNValidator:
    def __init__(self, xml_content):
        self.tree = ET.ElementTree(ET.fromstring(xml_content))
        self.root = self.tree.getroot()
        schema_dir = Path(__file__).parent / "schemas"
        dmn_dir = schema_dir / "dmn13"
        self.schema = xmlschema.XMLSchema(
            dmn_dir / "DMN13.xsd",
            validation="lax",  # Use lax validation to handle missing imports
            base_url=str(dmn_dir.absolute()),  # Set base URL for imports
        )

    def validate_structure(self):
        if self.root.tag != "definitions":
            return False, "Root element must be <definitions>."
        
        for decision in self.root.findall(".//decision"):
            if "id" not in decision.attrib or "name" not in decision.attrib:
                return False, "Each <decision> must have 'id' and 'name' attributes."
            
            decision_table = decision.find("decisionTable")
            if decision_table is None:
                return False, "<decision> must contain a <decisionTable>."
            
            inputs = decision_table.findall("input")
            outputs = decision_table.findall("output")
            rules = decision_table.findall("rule")
            
            if not inputs:
                return False, "<decisionTable> must have at least one <input>."
            if not outputs:
                return False, "<decisionTable> must have at least one <output>."
            if not rules:
                return False, "<decisionTable> must have at least one <rule>."
            
            for rule in rules:
                input_entries = rule.findall("inputEntry")
                output_entries = rule.findall("outputEntry")
                
                if len(input_entries) != len(inputs):
                    return False, "Each <rule> must have input entries matching the number of <input> elements."
                if len(output_entries) != len(outputs):
                    return False, "Each <rule> must have output entries matching the number of <output> elements."
        
        return True, "DMN structure is valid."
    
    def validate_against_xsd(self, xml_path):
        try:
            if self.schema.is_valid(xml_path):
                return True, "DMN XML is valid against DMN 1.3 XSD."
            else:
                return False, "DMN XML does not conform to DMN 1.3 standard."
        except Exception as e:
            return False, f"XSD Validation error: {str(e)}"