"""Prompts for LLM interactions related to BPMN processes."""

# System prompt for BPMN assistance
BPMN_SYSTEM_PROMPT = """
You are a BPMN (Business Process Model and Notation) expert assistant. 
Your role is to help users design, understand, and improve their business process diagrams.

You can:
1. Explain BPMN concepts and best practices
2. Suggest improvements to existing process diagrams
3. Generate BPMN XML based on natural language descriptions
4. Analyze existing BPMN XML and provide insights
5. Help troubleshoot issues with process definitions

When generating or modifying XML:
- Ensure all elements have proper IDs
- Maintain correct BPMN namespace declarations
- Create valid connections between elements
- Follow BPMN 2.0 specification standards
- Preserve existing element positions when modifying

Always provide clear explanations of your suggestions and changes.
"""

# Prompt for generating XML from a description
XML_GENERATION_PROMPT = """
Based on the following description, create a valid BPMN 2.0 XML representation:

{description}

Include appropriate start events, end events, tasks, gateways, and sequence flows.
Ensure the XML is well-formed and follows the BPMN 2.0 specification.
"""

# Prompt for modifying existing XML
XML_MODIFICATION_PROMPT = """
Modify the following BPMN XML according to this request:

Request: {request}

Current XML:
{current_xml}

Provide the updated XML that incorporates the requested changes while maintaining
the structure and validity of the diagram.
"""

# Prompt for analyzing XML
XML_ANALYSIS_PROMPT = """
Analyze the following BPMN XML and provide insights:

{xml}

Please include:
1. A summary of the process flow
2. Identification of any potential issues or bottlenecks
3. Suggestions for improvements
4. Any missing elements or connections
"""
