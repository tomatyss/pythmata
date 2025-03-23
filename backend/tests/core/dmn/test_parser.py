import pytest
from pythmata.core.dmn.parser import DMNParser

@pytest.mark.unit
class TestDMNParser:
    @classmethod
    def setup_class(cls):
        cls.valid_dmn = """
        <definitions xmlns="https://www.omg.org/spec/DMN/20191111/MODEL/" id="dmn-definitions">
            <decision id="decision1" name="Loan Approval">
                <decisionTable id="decision1_table">
                    <input label="Credit Score"/>
                    <input label="Income"/>
                    <output label="Approval"/>
                    <rule>
                        <inputEntry>>700</inputEntry>
                        <inputEntry>>50000</inputEntry>
                        <outputEntry>Approved</outputEntry>
                    </rule>
                </decisionTable>
            </decision>
        </definitions>
        """
        cls.invalid_dmn = "<definitions><decision></decision></definitions>"

    @pytest.mark.unit
    def test_parse_valid_dmn(self):
        parser = DMNParser(self.valid_dmn)
        decision_tables = parser.parse_decision_tables()
        assert len(decision_tables) == 1
        assert decision_tables[0]["id"] == "decision1_table"
        assert decision_tables[0]["inputs"] == ["Credit Score", "Income"]
        assert decision_tables[0]["outputs"] == ["Approval"]

    @pytest.mark.unit
    @pytest.mark.xfail
    def test_parse_invalid_dmn(self):
        parser = DMNParser(self.invalid_dmn)
        decision_tables = parser.parse_decision_tables()
        assert decision_tables == []
