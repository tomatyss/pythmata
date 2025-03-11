"""LLM service for interacting with language models using AISuite."""

from typing import Any, Dict, List

import aisuite as ai

from pythmata.core.bpmn.validator import BPMNValidator
from pythmata.core.websockets.chat_manager import chat_manager
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
        validate_xml: bool = False,
        max_validation_attempts: int = 3,
    ) -> Dict[str, Any]:
        """
        Generate a chat completion response.

        Args:
            messages: List of message objects with role and content
            model: Model identifier in format <provider>:<model-name>
            temperature: Controls randomness (0-1)
            max_tokens: Maximum tokens to generate
            validate_xml: Whether to validate and improve XML if found in the response
            max_validation_attempts: Maximum number of validation improvement attempts

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

            content = response.choices[0].message.content
            result = {
                "content": content,
                "model": model,
                "finish_reason": response.choices[0].finish_reason,
                "usage": usage,
            }

            # Validate XML in the response if requested
            if validate_xml:
                # Extract XML from response
                xml = None

                # Extract XML from markdown code blocks
                if "```xml" in content and "```" in content.split("```xml", 1)[1]:
                    xml = content.split("```xml", 1)[1].split("```", 1)[0].strip()
                elif "```" in content and "```" in content.split("```", 1)[1]:
                    # Try without language specifier
                    potential_xml = (
                        content.split("```", 1)[1].split("```", 1)[0].strip()
                    )
                    if potential_xml.startswith("<?xml") or potential_xml.startswith(
                        "<bpmn:"
                    ):
                        xml = potential_xml

                # If XML found, validate and improve it
                if xml:
                    logger.info(
                        "XML found in chat response, validating and improving..."
                    )
                    validation_result = await self.validate_and_improve_xml(
                        xml=xml,
                        model=model,
                        max_attempts=max_validation_attempts,
                        temperature=temperature,
                    )

                    # If validation improved the XML, update the content
                    if validation_result["improvement_attempts"] > 0:
                        improved_xml = validation_result["xml"]

                        # Replace the original XML with the improved version
                        if (
                            "```xml" in content
                            and "```" in content.split("```xml", 1)[1]
                        ):
                            new_content = (
                                content.split("```xml", 1)[0]
                                + "```xml\n"
                                + improved_xml
                                + "\n```"
                                + content.split("```xml", 1)[1].split("```", 1)[1]
                            )
                        else:
                            # For code blocks without language specifier
                            new_content = (
                                content.split("```", 1)[0]
                                + "```\n"
                                + improved_xml
                                + "\n```"
                                + content.split("```", 1)[1].split("```", 1)[1]
                            )

                        # Update the result with the improved content
                        result["content"] = new_content

                        # Add validation info to the result
                        result["xml_validation"] = {
                            "is_valid": validation_result["is_valid"],
                            "improvement_attempts": validation_result[
                                "improvement_attempts"
                            ],
                            "validation_errors": validation_result["validation_errors"],
                        }

                        validation_status = (
                            "valid" if validation_result["is_valid"] else "invalid"
                        )
                        logger.info(
                            f"XML in chat response is {validation_status} after {validation_result['improvement_attempts']} improvement attempts"
                        )

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
        validate: bool = True,
        max_validation_attempts: int = 3,
    ) -> Dict[str, Any]:
        """
        Generate BPMN XML from a natural language description.

        Args:
            description: Natural language description of the process
            model: Model identifier in format <provider>:<model-name>
            temperature: Controls randomness (0-1)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt to override default
            validate: Whether to validate and improve the XML
            max_validation_attempts: Maximum number of validation improvement attempts

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
                    explanation = content.split("```xml", 1)[0].strip()

            if not xml:
                logger.warning("Failed to extract valid XML from the LLM response")
                xml = ""

            # Validate and improve XML if requested
            validation_result = None
            if validate and xml:
                logger.info("Validating and improving generated XML...")
                validation_result = await self.validate_and_improve_xml(
                    xml=xml,
                    model=model,
                    max_attempts=max_validation_attempts,
                    temperature=temperature,
                    system_prompt=system_prompt,
                )

                # Use the validated/improved XML
                xml = validation_result["xml"]

                # Add validation info to the explanation
                if validation_result["improvement_attempts"] > 0:
                    validation_status = (
                        "valid" if validation_result["is_valid"] else "invalid"
                    )
                    explanation += f"\n\nXML validation: {validation_status} after {validation_result['improvement_attempts']} improvement attempts."

                    if (
                        not validation_result["is_valid"]
                        and validation_result["validation_errors"]
                    ):
                        explanation += "\nRemaining validation errors:\n"
                        for error in validation_result["validation_errors"]:
                            explanation += f"- {error['code']}: {error['message']}\n"

            result = {
                "xml": xml,
                "explanation": explanation,
                "model": model,
            }

            # Include validation info if available
            if validation_result:
                result["validation"] = {
                    "is_valid": validation_result["is_valid"],
                    "improvement_attempts": validation_result["improvement_attempts"],
                    "validation_errors": validation_result["validation_errors"],
                }

            return result

        except Exception as e:
            logger.error(f"XML generation failed: {str(e)}")
            raise

    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        client_id: str,
        model: str = "anthropic:claude-3-7-sonnet-latest",
        temperature: float = 0.5,
        max_tokens: int = 8192,
    ) -> str:
        """
        Stream a chat completion response token by token.

        Args:
            messages: List of message objects with role and content
            client_id: Client ID to stream tokens to
            model: Model identifier in format <provider>:<model-name>
            temperature: Controls randomness (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Complete response content as a string

        Raises:
            Exception: If the LLM API call fails
        """
        try:
            # Fix model format if needed (replace / with :)
            if "/" in model:
                model = model.replace("/", ":")
                logger.debug(f"Converted model format to: {model}")

            logger.debug(f"Starting streaming request to LLM model {model}")

            # Create streaming response
            response_stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            # Stream tokens to client
            content_buffer = ""
            try:
                for chunk in response_stream:
                    # Safely access chunk attributes with proper error handling
                    try:
                        if (
                            hasattr(chunk, "choices")
                            and len(chunk.choices) > 0
                            and hasattr(chunk.choices[0], "delta")
                            and hasattr(chunk.choices[0].delta, "content")
                        ):

                            delta_content = chunk.choices[0].delta.content
                            if delta_content:
                                content_buffer += delta_content
                                # Send token to client
                                await chat_manager.send_personal_message(
                                    client_id, "token", {"content": delta_content}
                                )
                    except AttributeError as attr_err:
                        # Log the specific attribute error but continue processing
                        logger.warning(
                            f"Attribute error while processing chunk: {attr_err}"
                        )
                        # Continue with the next chunk instead of failing the entire stream
                        continue
            except Exception as stream_err:
                # Handle any errors during stream processing
                logger.error(f"Error processing stream: {stream_err}")
                # If we have content so far, return it instead of failing completely
                if content_buffer:
                    return content_buffer
                raise

            logger.debug(f"Completed streaming response from LLM model {model}")
            return content_buffer

        except Exception as e:
            logger.error(f"LLM streaming error: {str(e)}")
            raise

    async def validate_and_improve_xml(
        self,
        xml: str,
        model: str = "anthropic:claude-3-7-sonnet-latest",
        max_attempts: int = 3,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        system_prompt: str = None,
    ) -> Dict[str, Any]:
        """
        Validate XML and attempt to improve it if validation fails.

        Args:
            xml: XML content to validate
            model: LLM model to use for improvements
            max_attempts: Maximum number of improvement attempts
            temperature: Temperature for LLM requests
            max_tokens: Maximum tokens for LLM requests
            system_prompt: Optional system prompt to override default

        Returns:
            Dictionary with validated XML, validation status, and improvement history
        """
        from pythmata.core.llm.prompts import BPMN_SYSTEM_PROMPT, XML_IMPROVEMENT_PROMPT

        # Initialize validator
        validator = BPMNValidator()

        # First validation
        validation_result = validator.validate(xml)

        # If already valid, return immediately
        if validation_result.is_valid:
            logger.info("XML is valid, no improvements needed")
            return {
                "xml": xml,
                "is_valid": True,
                "validation_errors": [],
                "improvement_attempts": 0,
            }

        # Track the best XML version (with fewest validation errors)
        best_xml = xml
        best_error_count = len(validation_result.errors)

        # Format validation errors for the prompt
        validation_errors_text = "\n".join(
            [f"- {error}" for error in validation_result.errors]
        )

        logger.info(
            f"XML validation failed with {best_error_count} errors. Attempting to improve..."
        )

        # Improvement loop
        attempts = 0
        improvement_history = []

        while not validation_result.is_valid and attempts < max_attempts:
            attempts += 1

            try:
                # Prepare improvement prompt
                prompt = XML_IMPROVEMENT_PROMPT.format(
                    validation_errors=validation_errors_text, original_xml=best_xml
                )

                # Use provided system prompt or default
                sys_prompt = system_prompt or BPMN_SYSTEM_PROMPT

                # Call LLM for improvement
                response = await self.chat_completion(
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                # Extract improved XML
                content = response["content"]
                improved_xml = None

                # Extract XML from markdown code blocks
                if "```xml" in content and "```" in content.split("```xml", 1)[1]:
                    improved_xml = (
                        content.split("```xml", 1)[1].split("```", 1)[0].strip()
                    )
                elif "```" in content and "```" in content.split("```", 1)[1]:
                    # Try without language specifier
                    potential_xml = (
                        content.split("```", 1)[1].split("```", 1)[0].strip()
                    )
                    if potential_xml.startswith("<?xml") or potential_xml.startswith(
                        "<bpmn:"
                    ):
                        improved_xml = potential_xml

                if not improved_xml:
                    logger.warning(
                        f"Attempt {attempts}: Failed to extract XML from improvement response"
                    )
                    improvement_history.append(
                        {
                            "attempt": attempts,
                            "success": False,
                            "error": "Failed to extract XML from response",
                        }
                    )
                    continue

                # Validate improved XML
                new_validation_result = validator.validate(improved_xml)
                new_error_count = len(new_validation_result.errors)

                # Record improvement attempt
                improvement_history.append(
                    {
                        "attempt": attempts,
                        "success": new_validation_result.is_valid,
                        "error_count": new_error_count,
                        "errors": (
                            [str(error) for error in new_validation_result.errors]
                            if not new_validation_result.is_valid
                            else []
                        ),
                    }
                )

                logger.info(
                    f"Attempt {attempts}: XML has {new_error_count} validation errors (was {best_error_count})"
                )

                # If valid or better than previous best, update best XML
                if new_validation_result.is_valid or new_error_count < best_error_count:
                    best_xml = improved_xml
                    best_error_count = new_error_count
                    validation_result = new_validation_result
                    validation_errors_text = "\n".join(
                        [f"- {error}" for error in validation_result.errors]
                    )

                    if new_validation_result.is_valid:
                        logger.info(
                            f"XML successfully validated after {attempts} attempts"
                        )
                        break

            except Exception as e:
                logger.error(
                    f"Error during XML improvement attempt {attempts}: {str(e)}"
                )
                improvement_history.append(
                    {"attempt": attempts, "success": False, "error": str(e)}
                )

        # Return best XML version with validation status
        return {
            "xml": best_xml,
            "is_valid": validation_result.is_valid,
            "validation_errors": [
                error.to_dict() for error in validation_result.errors
            ],
            "improvement_attempts": attempts,
            "improvement_history": improvement_history,
        }

    async def modify_xml(
        self,
        current_xml: str,
        request: str,
        model: str = "anthropic:claude-3-7-sonnet-latest",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        system_prompt: str = None,
        validate: bool = True,
        max_validation_attempts: int = 3,
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
            validate: Whether to validate and improve the XML
            max_validation_attempts: Maximum number of validation improvement attempts

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
                    explanation = content.split("```xml", 1)[0].strip()

            if not xml:
                logger.warning("Failed to extract valid XML from the LLM response")
                # Fall back to the original XML
                xml = current_xml

            # Validate and improve XML if requested
            validation_result = None
            if validate and xml:
                logger.info("Validating and improving modified XML...")
                validation_result = await self.validate_and_improve_xml(
                    xml=xml,
                    model=model,
                    max_attempts=max_validation_attempts,
                    temperature=temperature,
                    system_prompt=system_prompt,
                )

                # Use the validated/improved XML
                xml = validation_result["xml"]

                # Add validation info to the explanation
                if validation_result["improvement_attempts"] > 0:
                    validation_status = (
                        "valid" if validation_result["is_valid"] else "invalid"
                    )
                    explanation += f"\n\nXML validation: {validation_status} after {validation_result['improvement_attempts']} improvement attempts."

                    if (
                        not validation_result["is_valid"]
                        and validation_result["validation_errors"]
                    ):
                        explanation += "\nRemaining validation errors:\n"
                        for error in validation_result["validation_errors"]:
                            explanation += f"- {error['code']}: {error['message']}\n"

            result = {
                "xml": xml,
                "explanation": explanation,
                "model": model,
            }

            # Include validation info if available
            if validation_result:
                result["validation"] = {
                    "is_valid": validation_result["is_valid"],
                    "improvement_attempts": validation_result["improvement_attempts"],
                    "validation_errors": validation_result["validation_errors"],
                }

            return result

        except Exception as e:
            logger.error(f"XML modification failed: {str(e)}")
            raise
