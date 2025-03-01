"""Notification service task implementation."""

from typing import Any, Dict, List
from pythmata.core.services.base import ServiceTask
from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationServiceTask(ServiceTask):
    """
    Service task for sending notifications.
    
    This service task demonstrates how to create a custom service task
    that can be used in BPMN processes to send notifications through
    various channels.
    """
    
    @property
    def name(self) -> str:
        """
        Get the unique name of the service task.
        
        Returns:
            str: Unique identifier for this service task type
        """
        return "notification"
    
    @property
    def description(self) -> str:
        """
        Get a human-readable description of what the service task does.
        
        Returns:
            str: Description of the service task's purpose and behavior
        """
        return "Send notifications through various channels"
    
    @property
    def properties(self) -> List[Dict[str, Any]]:
        """
        Get the list of configurable properties for this service task.
        
        Returns:
            List[Dict[str, Any]]: List of property definitions
        """
        return [
            {
                "name": "channel",
                "label": "Channel",
                "type": "string",
                "required": True,
                "options": ["email", "sms", "slack", "webhook"],
                "default": "email",
                "description": "Notification channel to use",
            },
            {
                "name": "recipient",
                "label": "Recipient",
                "type": "string",
                "required": True,
                "description": "Recipient of the notification",
            },
            {
                "name": "subject",
                "label": "Subject",
                "type": "string",
                "required": True,
                "description": "Subject or title of the notification",
            },
            {
                "name": "message",
                "label": "Message",
                "type": "string",
                "required": True,
                "description": "Content of the notification",
            },
            {
                "name": "priority",
                "label": "Priority",
                "type": "string",
                "required": False,
                "options": ["low", "normal", "high", "urgent"],
                "default": "normal",
                "description": "Priority of the notification",
            },
            {
                "name": "template",
                "label": "Template",
                "type": "string",
                "required": False,
                "description": "Template name to use for formatting the message",
            },
        ]
    
    async def execute(
        self, context: Dict[str, Any], properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the notification task.
        
        Args:
            context: Execution context containing token, variables, etc.
            properties: Configuration properties for this execution
            
        Returns:
            Dict[str, Any]: Result of the execution
            
        Raises:
            Exception: If sending the notification fails
        """
        # Extract properties
        channel = properties.get("channel", "email")
        recipient = properties.get("recipient", "")
        subject = properties.get("subject", "")
        message = properties.get("message", "")
        priority = properties.get("priority", "normal")
        template = properties.get("template")
        
        # Access process variables and token information
        variables = context.get("variables", {})
        token = context.get("token")
        instance_id = token.instance_id if token else None
        
        # Log the notification attempt
        logger.info(
            f"Sending {priority} priority notification via {channel} to {recipient}"
        )
        logger.debug(f"Notification subject: {subject}")
        logger.debug(f"Process instance: {instance_id}")
        
        # In a real implementation, we would send the notification through the specified channel
        # For this example, we'll just simulate the sending
        
        # Simulate different channel implementations
        if channel == "email":
            # Simulate sending an email
            logger.info(f"Simulating email to {recipient}: {subject}")
            # In a real implementation, we would use smtplib or a similar library
        elif channel == "sms":
            # Simulate sending an SMS
            logger.info(f"Simulating SMS to {recipient}: {subject}")
            # In a real implementation, we would use a service like Twilio
        elif channel == "slack":
            # Simulate sending a Slack message
            logger.info(f"Simulating Slack message to {recipient}: {subject}")
            # In a real implementation, we would use the Slack API
        elif channel == "webhook":
            # Simulate sending a webhook
            logger.info(f"Simulating webhook to {recipient}: {subject}")
            # In a real implementation, we would use requests or aiohttp
        else:
            # Unknown channel
            error_msg = f"Unknown notification channel: {channel}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg,
            }
        
        # Return success result
        return {
            "status": "success",
            "channel": channel,
            "recipient": recipient,
            "subject": subject,
            "priority": priority,
            "message": "Notification sent successfully",
        }
