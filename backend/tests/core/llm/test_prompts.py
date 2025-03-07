"""Tests for LLM prompts."""

from pythmata.core.llm.prompts import (
    BPMN_SYSTEM_PROMPT,
    XML_ANALYSIS_PROMPT,
    XML_GENERATION_PROMPT,
    XML_MODIFICATION_PROMPT,
)


def test_bpmn_system_prompt():
    """Test that the BPMN system prompt contains expected content."""
    assert isinstance(BPMN_SYSTEM_PROMPT, str)
    assert len(BPMN_SYSTEM_PROMPT) > 0

    # Check for key phrases that should be in the prompt
    assert "BPMN" in BPMN_SYSTEM_PROMPT
    assert "expert assistant" in BPMN_SYSTEM_PROMPT

    # Check for key capabilities
    assert "Explain BPMN concepts" in BPMN_SYSTEM_PROMPT
    assert "Generate BPMN XML" in BPMN_SYSTEM_PROMPT
    assert "Analyze existing BPMN XML" in BPMN_SYSTEM_PROMPT

    # Check for XML generation guidelines
    assert "proper IDs" in BPMN_SYSTEM_PROMPT
    assert "BPMN 2.0 specification" in BPMN_SYSTEM_PROMPT


def test_xml_generation_prompt():
    """Test that the XML generation prompt contains expected content and placeholders."""
    assert isinstance(XML_GENERATION_PROMPT, str)
    assert len(XML_GENERATION_PROMPT) > 0

    # Check for key phrases
    assert "create a valid BPMN 2.0 XML" in XML_GENERATION_PROMPT

    # Check for placeholders
    assert "{description}" in XML_GENERATION_PROMPT

    # Check for formatting instructions
    assert "start events" in XML_GENERATION_PROMPT
    assert "end events" in XML_GENERATION_PROMPT
    assert "tasks" in XML_GENERATION_PROMPT
    assert "gateways" in XML_GENERATION_PROMPT
    assert "sequence flows" in XML_GENERATION_PROMPT


def test_xml_modification_prompt():
    """Test that the XML modification prompt contains expected content and placeholders."""
    assert isinstance(XML_MODIFICATION_PROMPT, str)
    assert len(XML_MODIFICATION_PROMPT) > 0

    # Check for key phrases
    assert "Modify the following BPMN XML" in XML_MODIFICATION_PROMPT

    # Check for placeholders
    assert "{request}" in XML_MODIFICATION_PROMPT
    assert "{current_xml}" in XML_MODIFICATION_PROMPT

    # Check for instructions
    assert "maintaining" in XML_MODIFICATION_PROMPT
    assert "structure and validity" in XML_MODIFICATION_PROMPT


def test_xml_analysis_prompt():
    """Test that the XML analysis prompt contains expected content and placeholders."""
    assert isinstance(XML_ANALYSIS_PROMPT, str)
    assert len(XML_ANALYSIS_PROMPT) > 0

    # Check for key phrases
    assert "Analyze the following BPMN XML" in XML_ANALYSIS_PROMPT

    # Check for placeholders
    assert "{xml}" in XML_ANALYSIS_PROMPT

    # Check for analysis instructions
    assert "summary of the process flow" in XML_ANALYSIS_PROMPT
    assert "potential issues" in XML_ANALYSIS_PROMPT
    assert "Suggestions for improvements" in XML_ANALYSIS_PROMPT


def test_prompt_formatting():
    """Test that prompts can be properly formatted with sample data."""
    # Test XML generation prompt formatting
    description = "Create a simple approval process with two tasks"
    formatted_generation = XML_GENERATION_PROMPT.format(description=description)
    assert description in formatted_generation

    # Test XML modification prompt formatting
    request = "Add a service task after the first task"
    current_xml = "<bpmn:definitions></bpmn:definitions>"
    formatted_modification = XML_MODIFICATION_PROMPT.format(
        request=request, current_xml=current_xml
    )
    assert request in formatted_modification
    assert current_xml in formatted_modification

    # Test XML analysis prompt formatting
    xml = "<bpmn:definitions><bpmn:process></bpmn:process></bpmn:definitions>"
    formatted_analysis = XML_ANALYSIS_PROMPT.format(xml=xml)
    assert xml in formatted_analysis
