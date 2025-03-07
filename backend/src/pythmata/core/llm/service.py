"""LLM service for interacting with language models using AISuite."""

from typing import Any, Dict, List, Optional

import aisuite as ai

from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class LlmService:
    """
    Service for interacting with LLM models using AISuite.

    This service provides a unified interface to multiple LLM providers
    through the AISuite library, supporting OpenAI and Anthropic models.

    Attributes:
        client: AISuite client for making API calls
    """

    def __init__(self):
        """Initialize the LLM service with AISuite client."""
        self.client = ai.Client()
        logger.info("LLM service initialized with AISuite")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "anthropic:claude-3-7-sonnet-latest",
        temperature: float = 0.5,
        max_tokens: int = 8192,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a chat completion response.

        Args:
            messages: List of message objects with role and content
            model: Model identifier in format <provider>:<model-name>
            temperature: Controls randomness (0-1)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt to override default (deprecated, use system role in messages instead)

        Returns:
            Response from the LLM including content and metadata

        Raises:
            Exception: If the LLM API call fails
        """
        try:
            # Fix model format if needed (replace / with :)
            if "/" in model:
                model = model.replace("/", ":")
                logger.debug(f"Converted model format to: {model}")

            logger.debug(
                f"Sending request to LLM model {model} with {len(messages)} messages"
            )

            # Let aisuite handle the provider-specific differences
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Extract usage information if available
            usage = {}
            try:
                if hasattr(response, "usage"):
                    # Handle different response structures from different providers
                    if isinstance(response.usage, dict):
                        # OpenAI format
                        usage = {
                            "prompt_tokens": response.usage.get("prompt_tokens", 0),
                            "completion_tokens": response.usage.get(
                                "completion_tokens", 0
                            ),
                            "total_tokens": response.usage.get("total_tokens", 0),
                        }
                    else:
                        # Anthropic format
                        input_tokens = getattr(response.usage, "input_tokens", 0)
                        output_tokens = getattr(response.usage, "output_tokens", 0)
                        usage = {
                            "prompt_tokens": input_tokens,
                            "completion_tokens": output_tokens,
                            "total_tokens": input_tokens + output_tokens,
                        }
            except Exception as e:
                logger.warning(f"Failed to extract usage information: {str(e)}")
                # Set default usage to avoid errors
                usage = {"total_tokens": 0}

            result = {
                "content": response.choices[0].message.content,
                "model": model,
                "finish_reason": response.choices[0].finish_reason,
                "usage": usage,
            }

            logger.debug(f"Received response from LLM model {model}")
            return result

        except Exception as e:
            logger.error(f"LLM service error: {str(e)}")
            raise

    async def generate_xml(
        self,
        description: str,
        model: str = "anthropic:claude-3-7-sonnet-latest",
        temperature: float = 0.3,  # Lower temperature for more deterministic XML generation
        max_tokens: int = 2000,
        system_prompt: str = None,
    ) -> Dict[str, Any]:
        """
        Generate BPMN XML from a natural language description.

        Args:
            description: Natural language description of the process
            model: Model identifier in format <provider>:<model-name>
            temperature: Controls randomness (0-1)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt to override default

        Returns:
            Dictionary containing the generated XML and explanation

        Raises:
            Exception: If XML generation fails
        """
        from pythmata.core.llm.prompts import BPMN_SYSTEM_PROMPT, XML_GENERATION_PROMPT

        try:
            # Prepare prompt
            prompt = XML_GENERATION_PROMPT.format(description=description)

            # Use provided system prompt or default
            sys_prompt = system_prompt or BPMN_SYSTEM_PROMPT

            # Call LLM service
            response = await self.chat_completion(
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": prompt},
                ],
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Extract XML from response
            content = response["content"]
            xml = None
            explanation = content

            # Extract XML from markdown code blocks
            if "```xml" in content and "```" in content.split("```xml", 1)[1]:
                xml = content.split("```xml", 1)[1].split("```", 1)[0].strip()
                explanation = content.split("```xml", 1)[0].strip()
            elif "```" in content and "```" in content.split("```", 1)[1]:
                # Try without language specifier
                potential_xml = content.split("```", 1)[1].split("```", 1)[0].strip()
                if potential_xml.startswith("<?xml") or potential_xml.startswith(
                    "<bpmn:"
                ):
                    xml = potential_xml
                    explanation = content.split("```", 1)[0].strip()

            if not xml:
                logger.warning("Failed to extract valid XML from the LLM response")
                xml = ""

            return {"xml": xml, "explanation": explanation, "model": model}

        except Exception as e:
            logger.error(f"XML generation failed: {str(e)}")
            raise

    async def modify_xml(
        self,
        current_xml: str,
        request: str,
        model: str = "anthropic:claude-3-7-sonnet-latest",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        system_prompt: str = None,
    ) -> Dict[str, Any]:
        """
        Modify existing BPMN XML based on a natural language request.

        Args:
            current_xml: Existing BPMN XML to modify
            request: Natural language description of the requested changes
            model: Model identifier in format <provider>:<model-name>
            temperature: Controls randomness (0-1)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt to override default

        Returns:
            Dictionary containing the modified XML and explanation

        Raises:
            Exception: If XML modification fails
        """
        from pythmata.core.llm.prompts import (
            BPMN_SYSTEM_PROMPT,
            XML_MODIFICATION_PROMPT,
        )

        try:
            # Prepare prompt
            prompt = XML_MODIFICATION_PROMPT.format(
                request=request, current_xml=current_xml
            )

            # Use provided system prompt or default
            sys_prompt = system_prompt or BPMN_SYSTEM_PROMPT

            # Call LLM service
            response = await self.chat_completion(
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": prompt},
                ],
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Extract XML from response (similar to generate_xml)
            content = response["content"]
            xml = None
            explanation = content

            # Extract XML from markdown code blocks
            if "```xml" in content and "```" in content.split("```xml", 1)[1]:
                xml = content.split("```xml", 1)[1].split("```", 1)[0].strip()
                explanation = content.split("```xml", 1)[0].strip()
            elif "```" in content and "```" in content.split("```", 1)[1]:
                # Try without language specifier
                potential_xml = content.split("```", 1)[1].split("```", 1)[0].strip()
                if potential_xml.startswith("<?xml") or potential_xml.startswith(
                    "<bpmn:"
                ):
                    xml = potential_xml
                    explanation = content.split("```", 1)[0].strip()

            if not xml:
                logger.warning("Failed to extract valid XML from the LLM response")
                # Fall back to the original XML
                xml = current_xml

            return {"xml": xml, "explanation": explanation, "model": model}

        except Exception as e:
            logger.error(f"XML modification failed: {str(e)}")
            raise
