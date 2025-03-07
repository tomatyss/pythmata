"""HTTP service task implementation."""

import json
from typing import Any, Dict, List

import aiohttp

from pythmata.core.services.base import ServiceTask


class HttpServiceTask(ServiceTask):
    """
    Service task for making HTTP requests.

    Allows processes to make HTTP requests to external services and APIs.
    Supports GET, POST, PUT, DELETE methods with configurable headers and body.
    """

    @property
    def name(self) -> str:
        """
        Get the unique name of the service task.

        Returns:
            str: Unique identifier for this service task type
        """
        return "http"

    @property
    def description(self) -> str:
        """
        Get a human-readable description of what the service task does.

        Returns:
            str: Description of the service task's purpose and behavior
        """
        return "Make HTTP requests to external services and APIs"

    @property
    def properties(self) -> List[Dict[str, Any]]:
        """
        Get the list of configurable properties for this service task.

        Returns:
            List[Dict[str, Any]]: List of property definitions
        """
        return [
            {
                "name": "url",
                "label": "URL",
                "type": "string",
                "required": True,
                "description": "URL to send the request to",
            },
            {
                "name": "method",
                "label": "Method",
                "type": "string",
                "required": True,
                "default": "GET",
                "options": ["GET", "POST", "PUT", "DELETE"],
                "description": "HTTP method to use",
            },
            {
                "name": "headers",
                "label": "Headers",
                "type": "json",
                "required": False,
                "default": "{}",
                "description": "HTTP headers as JSON object",
            },
            {
                "name": "body",
                "label": "Body",
                "type": "json",
                "required": False,
                "description": "Request body as JSON",
            },
            {
                "name": "timeout",
                "label": "Timeout (seconds)",
                "type": "number",
                "required": False,
                "default": 30,
                "description": "Request timeout in seconds",
            },
            {
                "name": "output_mapping",
                "label": "Output Mapping",
                "type": "json",
                "required": False,
                "default": "{}",
                "description": "Mapping of response fields to process variables",
            },
        ]

    async def execute(
        self, context: Dict[str, Any], properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the HTTP request.

        Args:
            context: Execution context containing token, variables, etc.
            properties: Configuration properties for this execution

        Returns:
            Dict[str, Any]: Result of the execution with response data

        Raises:
            Exception: If the HTTP request fails
        """
        url = properties.get("url")
        method = properties.get("method", "GET").upper()
        headers = properties.get("headers", {})
        body = properties.get("body")
        timeout = float(properties.get("timeout", 30))

        # Parse JSON properties if they're strings
        if isinstance(headers, str):
            headers = json.loads(headers)
        if isinstance(body, str) and body:
            body = json.loads(body)

        # Prepare result
        result = {
            "url": url,
            "method": method,
            "status_code": None,
            "response": None,
            "headers": None,
            "error": None,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body if body else None,
                    timeout=timeout,
                ) as response:
                    result["status_code"] = response.status
                    result["headers"] = dict(response.headers)

                    # Try to parse response as JSON, fall back to text
                    try:
                        result["response"] = await response.json()
                    except:
                        result["response"] = await response.text()

                    # Raise exception for error status codes
                    if response.status >= 400:
                        error_msg = f"HTTP request failed with status {response.status}"
                        result["error"] = error_msg
                        raise Exception(error_msg)

            return result
        except Exception as e:
            if "error" not in result or not result["error"]:
                result["error"] = str(e)
            raise
