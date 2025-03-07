# Creating Custom Service Tasks

This guide explains how to create custom service tasks for Pythmata using the plugin system.

## Plugin System Overview

Pythmata's plugin system allows you to extend the workflow engine with custom service tasks without modifying the core codebase. Plugins are discovered and loaded automatically at startup from the configured plugin directory.

## Plugin Structure

A plugin is a Python package with the following structure:

```
my_plugin/
├── __init__.py          # Plugin initialization and registration
├── requirements.txt     # Optional dependencies
└── my_task.py           # Service task implementation
```

## Creating a Custom Service Task

### Step 1: Create the Plugin Directory

Create a directory for your plugin in the `plugins` directory:

```bash
mkdir -p plugins/my_plugin
```

### Step 2: Implement the Service Task

Create a Python file (e.g., `my_task.py`) with your service task implementation:

```python
from typing import Any, Dict, List
from pythmata.core.services.base import ServiceTask

class MyCustomServiceTask(ServiceTask):
    """
    Custom service task that does something useful.
    
    Provide a clear description of what your service task does.
    """
    
    @property
    def name(self) -> str:
        """
        Get the unique name of the service task.
        
        Returns:
            str: Unique identifier for this service task type
        """
        return "my_custom_task"  # This is the name that will be used in BPMN diagrams
    
    @property
    def description(self) -> str:
        """
        Get a human-readable description of what the service task does.
        
        Returns:
            str: Description of the service task's purpose and behavior
        """
        return "This is my custom service task that does something useful"
    
    @property
    def properties(self) -> List[Dict[str, Any]]:
        """
        Get the list of configurable properties for this service task.
        
        Returns:
            List[Dict[str, Any]]: List of property definitions
        """
        return [
            {
                "name": "param1",
                "label": "Parameter 1",
                "type": "string",
                "required": True,
                "description": "First parameter description",
            },
            {
                "name": "param2",
                "label": "Parameter 2",
                "type": "number",
                "required": False,
                "default": 42,
                "description": "Second parameter description",
            },
            # Add more properties as needed
        ]
    
    async def execute(
        self, context: Dict[str, Any], properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the service task with the given context and properties.
        
        Args:
            context: Execution context containing token, variables, etc.
            properties: Configuration properties for this execution
            
        Returns:
            Dict[str, Any]: Result of the execution
            
        Raises:
            Exception: If execution fails
        """
        # Access properties
        param1 = properties.get("param1")
        param2 = properties.get("param2", 42)  # Use default if not provided
        
        # Access process variables
        variables = context.get("variables", {})
        
        # Access token information
        token = context.get("token")
        instance_id = token.instance_id if token else None
        
        # Your custom logic here
        result = {
            "status": "success",
            "message": f"Executed with param1={param1}, param2={param2}",
            # Add more result data as needed
        }
        
        return result
```

### Step 3: Register the Service Task

Create an `__init__.py` file in your plugin directory to register the service task:

```python
"""
My custom plugin for Pythmata.

This plugin provides custom service tasks for specific use cases.
"""

from pythmata.core.services.registry import get_service_task_registry
from .my_task import MyCustomServiceTask

# Register the service task
registry = get_service_task_registry()
registry.register(MyCustomServiceTask)

# You can register multiple service tasks if needed
```

### Step 4: Specify Dependencies (Optional)

If your service task requires additional Python packages, create a `requirements.txt` file:

```
# requirements.txt
requests>=2.28.0
pyyaml>=6.0
```

## Installing the Plugin

### Option 1: Local Development

1. Place your plugin directory in the `plugins` directory of your Pythmata project:

```bash
cp -r my_plugin /path/to/pythmata/plugins/
```

2. Start Pythmata with Docker Compose:

```bash
docker-compose up
```

### Option 2: Custom Docker Image

Create a custom Docker image that includes your plugins:

```dockerfile
FROM pythmata:latest

# Copy your plugins
COPY ./my_plugins /app/plugins/

# Install plugin dependencies
RUN for plugin_dir in /app/plugins/*/; do \
      if [ -f "${plugin_dir}requirements.txt" ]; then \
        pip install -r "${plugin_dir}requirements.txt"; \
      fi \
    done
```

## Using Custom Service Tasks in BPMN

Once your plugin is loaded, you can use your custom service task in BPMN diagrams:

1. Add a service task to your diagram
2. Configure the service task with the appropriate properties:
   - Set the `taskName` property to the name of your registered service task (e.g., `my_custom_task`)
   - Configure the task-specific properties as needed

## Example: Email Service Task

Here's a complete example of a service task that sends emails:

```python
"""Email service task implementation."""

from typing import Any, Dict, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from pythmata.core.services.base import ServiceTask


class EmailServiceTask(ServiceTask):
    """
    Service task for sending emails.
    
    Allows processes to send emails with configurable recipients, subject, and content.
    """
    
    @property
    def name(self) -> str:
        """
        Get the unique name of the service task.
        
        Returns:
            str: Unique identifier for this service task type
        """
        return "email"
    
    @property
    def description(self) -> str:
        """
        Get a human-readable description of what the service task does.
        
        Returns:
            str: Description of the service task's purpose and behavior
        """
        return "Send emails to specified recipients"
    
    @property
    def properties(self) -> List[Dict[str, Any]]:
        """
        Get the list of configurable properties for this service task.
        
        Returns:
            List[Dict[str, Any]]: List of property definitions
        """
        return [
            {
                "name": "to",
                "label": "To",
                "type": "string",
                "required": True,
                "description": "Recipient email address(es), comma-separated",
            },
            {
                "name": "subject",
                "label": "Subject",
                "type": "string",
                "required": True,
                "description": "Email subject",
            },
            {
                "name": "body",
                "label": "Body",
                "type": "string",
                "required": True,
                "description": "Email body content",
            },
            {
                "name": "smtp_server",
                "label": "SMTP Server",
                "type": "string",
                "required": False,
                "default": "smtp.example.com",
                "description": "SMTP server address",
            },
            {
                "name": "smtp_port",
                "label": "SMTP Port",
                "type": "number",
                "required": False,
                "default": 587,
                "description": "SMTP server port",
            },
            {
                "name": "username",
                "label": "Username",
                "type": "string",
                "required": False,
                "description": "SMTP authentication username",
            },
            {
                "name": "password",
                "label": "Password",
                "type": "string",
                "required": False,
                "description": "SMTP authentication password",
            },
        ]
    
    async def execute(
        self, context: Dict[str, Any], properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the email sending task.
        
        Args:
            context: Execution context containing token, variables, etc.
            properties: Configuration properties for this execution
            
        Returns:
            Dict[str, Any]: Result of the execution
            
        Raises:
            Exception: If sending the email fails
        """
        # Extract properties
        to_addresses = properties.get("to", "").split(",")
        subject = properties.get("subject", "")
        body = properties.get("body", "")
        smtp_server = properties.get("smtp_server", "smtp.example.com")
        smtp_port = int(properties.get("smtp_port", 587))
        username = properties.get("username")
        password = properties.get("password")
        
        # Create message
        message = MIMEMultipart()
        message["From"] = username
        message["To"] = ", ".join(to_addresses)
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))
        
        try:
            # Connect to server and send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(message)
            server.quit()
            
            return {
                "status": "success",
                "to": to_addresses,
                "subject": subject,
                "message": "Email sent successfully",
            }
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            return {
                "status": "error",
                "error": error_msg,
            }
```

## Troubleshooting

### Plugin Not Loading

If your plugin is not being loaded:

1. Check the logs for any errors during plugin discovery
2. Verify that your plugin directory structure is correct
3. Ensure that the `__init__.py` file correctly registers your service task
4. Check that the plugin directory is correctly mounted in Docker

### Service Task Not Appearing

If your service task is not appearing in the list of available tasks:

1. Check that the service task is properly registered in the `__init__.py` file
2. Verify that the service task class correctly inherits from `ServiceTask`
3. Ensure that the `name` property returns a unique identifier

### Dependency Issues

If your plugin has dependency issues:

1. Check that all required packages are listed in `requirements.txt`
2. Verify that the dependencies are being installed correctly
3. Check for version conflicts with the core application dependencies

## Best Practices

1. **Unique Names**: Ensure your service task names are unique across the application.
2. **Clear Documentation**: Provide clear descriptions for your service task and its properties.
3. **Error Handling**: Implement robust error handling in your `execute` method.
4. **Asynchronous Operations**: Use `async/await` for any I/O operations to avoid blocking the process engine.
5. **Testing**: Write unit tests for your service tasks to ensure they work correctly.
6. **Security**: Be careful with sensitive information like passwords; consider using environment variables or a secure configuration store.
