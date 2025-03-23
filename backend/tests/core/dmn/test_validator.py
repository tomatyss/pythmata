import pytest
from pythmata.core.dmn.validator import DMNValidator

@pytest.mark.unit
class TestDMNValidator:
    @classmethod
    def setup_class(cls):
        cls.valid_dmn = """
        <definitions xmlns="https://www.omg.org/spec/DMN/20191111/MODEL/" id="dmn-definitions" name="DMN Definitions">
            <decision id="decision1" name="Loan Approval">
                <decisionTable id="decision1_table">
                    <input label="Credit Score"/>
                    <input label="Income"/>
                    <output label="Approval"/>
                    <rule>
                        <inputEntry>&gt;700</inputEntry>
                        <inputEntry>&gt;50000</inputEntry>
                        <outputEntry>Approved</outputEntry>
                    </rule>
                    <rule>
                        <inputEntry>&lt;=700</inputEntry>
                        <inputEntry>&lt;=50000</inputEntry>
                        <outputEntry>Denied</outputEntry>
                    </rule>
                </decisionTable>
            </decision>
        </definitions>
        """
        cls.invalid_dmn = """
        <definitions>
            <decision id="decision1">
                <decisionTable>
                    <input label="Credit Score"/>
                    <output label="Approval"/>
                    <rule>
                        <outputEntry>Approved</outputEntry>
                    </rule>
                </decisionTable>
            </decision>
        </definitions>
        """

    @pytest.mark.unit
    @pytest.mark.xfail
    def test_invalid_dmn_structure(self):
        validator = DMNValidator(self.invalid_dmn)
        is_valid, message = validator.validate_structure()
        assert not is_valid
        assert message != "DMN structure is valid."

    @pytest.mark.unit
    def test_valid_dmn_structure(self):
        validator = DMNValidator(self.valid_dmn)
        is_valid, message = validator.validate_structure()
        assert is_valid
        assert message == "DMN structure is valid."