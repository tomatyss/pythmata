import pytest
from pythmata.core.dmn.builders import DMNBuilder

@pytest.mark.unit
class TestDMNBuilder:
    @pytest.mark.unit
    def test_build_dmn(self):
        builder = DMNBuilder()
        decision_table_data = {
            "id": "decision1_table",
            "name": "Loan Approval",
            "inputs": ["Credit Score", "Income"],
            "outputs": ["Approval"],
            "rules": [
                {"inputs": [">700", ">50000"], "output": "Approved"},
                {"inputs": ["<=700", "<=50000"], "output": "Denied"},
            ],
        }
        dmn_xml = builder.build_decision_table(decision_table_data)

        assert "<decision id=\"decision1_table\"" in dmn_xml
        assert "<input label=\"Credit Score\"" in dmn_xml
        assert "<output label=\"Approval\"" in dmn_xml
        assert "<inputEntry>&gt;700</inputEntry>" in dmn_xml
        assert "<outputEntry>Approved</outputEntry>" in dmn_xml
