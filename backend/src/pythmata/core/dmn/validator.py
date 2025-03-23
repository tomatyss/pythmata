import xml.etree.ElementTree as ET
import xmlschema
from pathlib import Path


class DMNValidator:
    def __init__(self, xml_content):
        self.tree = ET.ElementTree(ET.fromstring(xml_content))
        self.root = self.tree.getroot()
        self.namespace = {"dmn": "https://www.omg.org/spec/DMN/20191111/MODEL/"}

    def validate_structure(self):
        if self.root.tag != f"{{{self.namespace['dmn']}}}definitions":
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