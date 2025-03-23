import xml.etree.ElementTree as ET

class DMNBuilder:
    def __init__(self, namespace="https://www.omg.org/spec/DMN/20191111/MODEL/"):
        self.namespace = namespace
        self.root = ET.Element("definitions", {
            "xmlns": self.namespace,
            "id": "dmn-definitions",
            "name": "DMN Definitions",
            "namespace": self.namespace
        })

    def add_decision_table(self, decision_id, decision_name, inputs, outputs, rules):
        decision = ET.SubElement(self.root, "decision", {"id": decision_id, "name": decision_name})
        decision_table = ET.SubElement(decision, "decisionTable", {"id": f"{decision_id}_table"})
        
        for input_name in inputs:
            input_element = ET.SubElement(decision_table, "input", {"label": input_name})
            ET.SubElement(input_element, "inputExpression", {"typeRef": "string"})
        
        for output_name in outputs:
            ET.SubElement(decision_table, "output", {"label": output_name})
        
        for rule in rules:
            rule_element = ET.SubElement(decision_table, "rule")
            for input_value in rule["inputs"]:
                ET.SubElement(rule_element, "inputEntry").text = f"{input_value}"
            for output_value in rule["outputs"]:
                ET.SubElement(rule_element, "outputEntry").text = f"{output_value}"
    
    def to_xml(self):
        return ET.tostring(self.root, encoding="unicode")