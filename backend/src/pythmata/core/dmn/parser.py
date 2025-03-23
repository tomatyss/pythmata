import xml.etree.ElementTree as ET

class DMNParser:
    def __init__(self, xml_content):
        self.tree = ET.ElementTree(ET.fromstring(xml_content))
        self.root = self.tree.getroot()

    def get_decision_tables(self):
        decision_tables = []
        for decision in self.root.findall(".//decision"):
            decision_id = decision.get("id")
            decision_name = decision.get("name")
            decision_table = decision.find("decisionTable")
            
            if decision_table is None:
                continue
            
            inputs = [inp.get("label") for inp in decision_table.findall("input")]
            outputs = [out.get("label") for out in decision_table.findall("output")]
            
            rules = []
            for rule in decision_table.findall("rule"):
                input_entries = [entry.text for entry in rule.findall("inputEntry")]
                output_entries = [entry.text for entry in rule.findall("outputEntry")]
                rules.append({"inputs": input_entries, "outputs": output_entries})
            
            decision_tables.append({
                "id": decision_id,
                "name": decision_name,
                "inputs": inputs,
                "outputs": outputs,
                "rules": rules
            })
        
        return decision_tables