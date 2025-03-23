import xml.etree.ElementTree as ET
import re

class DMNBuilder:
    def __init__(self, namespace="https://www.omg.org/spec/DMN/20191111/MODEL/"):
        self.namespace = namespace
        self.root = ET.Element("definitions", {
            "xmlns": self.namespace,
            "id": "dmn-definitions",
            "name": "DMN Definitions",
            "namespace": self.namespace
        })
        self.dmn_prefix = "{%s}" % self.namespace

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
    
    def build_decision_table(self, decision_data):
        definitions = ET.Element(f"{self.dmn_prefix}definitions", {
            "xmlns": self.namespace,
            "id": "dmn-definitions",
            "name": "DMN Definitions"
        })

        decision = ET.SubElement(definitions, f"{self.dmn_prefix}decision", {
            "id": decision_data["id"],
            "name": decision_data["name"]
        })

        decision_table = ET.SubElement(decision, f"{self.dmn_prefix}decisionTable", {
            "id": f"{decision_data['id']}_table"
        })

        for input_label in decision_data["inputs"]:
            ET.SubElement(decision_table, f"{self.dmn_prefix}input", {"label": input_label})

        for output_label in decision_data["outputs"]:
            ET.SubElement(decision_table, f"{self.dmn_prefix}output", {"label": output_label})

        for rule in decision_data["rules"]:
            rule_element = ET.SubElement(decision_table, f"{self.dmn_prefix}rule")

            for input_entry in rule["inputs"]:
                input_entry_element = ET.SubElement(rule_element, f"{self.dmn_prefix}inputEntry")
                input_entry_element.text = input_entry

            output_entry_element = ET.SubElement(rule_element, f"{self.dmn_prefix}outputEntry")
            output_entry_element.text = rule["output"]

        # Convert XML tree to string
        dmn_xml = ET.tostring(definitions, encoding="utf-8").decode("utf-8")

        # Fix namespace prefix issue (removes ns0)
        dmn_xml = re.sub(r'xmlns:ns\d+="[^"]+"', '', dmn_xml)  # Remove unwanted xmlns attributes
        dmn_xml = re.sub(r'ns\d+:', '', dmn_xml)  # Remove ns0: prefix

        return dmn_xml