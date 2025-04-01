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

    def parse_decision_tables(self):
        """
        Extracts decision tables from DMN XML.

        Returns:
            List of dictionaries containing:
            - "id": Decision table ID
            - "name": Decision name
            - "inputs": List of input labels
            - "outputs": List of output labels
            - "rules": List of rule dictionaries with inputs and outputs
        """
        root = self.tree.getroot()
        namespace = {'dmn': "https://www.omg.org/spec/DMN/20191111/MODEL/"}

        decision_tables = []
        for decision in root.findall("dmn:decision", namespace):
            decision_id = decision.get("id")
            decision_name = decision.get("name", "")

            decision_table = decision.find("dmn:decisionTable", namespace)
            if decision_table is None:
                continue

            table_id = decision_table.get("id", "")

            inputs = [inp.get("label") for inp in decision_table.findall("dmn:input", namespace)]
            outputs = [out.get("label") for out in decision_table.findall("dmn:output", namespace)]

            rules = []
            for rule in decision_table.findall("dmn:rule", namespace):
                input_entries = [entry.text.strip() for entry in rule.findall("dmn:inputEntry", namespace)]
                output_entry = rule.find("dmn:outputEntry", namespace)
                output_value = output_entry.text.strip() if output_entry is not None else ""

                rules.append({"inputs": input_entries, "output": output_value})

            decision_tables.append({
                "id": table_id,
                "name": decision_name,
                "inputs": inputs,
                "outputs": outputs,
                "rules": rules,
            })

        return decision_tables