# Service Tasks

Service tasks in Pythmata allow you to extend the BPMN engine with custom functionality that can be executed when a token reaches a service task node in a BPMN diagram.

## Built-in Service Tasks

Pythmata comes with several built-in service tasks:

### HTTP Service Task

The HTTP service task allows processes to make HTTP requests to external services and APIs.

**Properties:**
- `url`: URL to send the request to (required)
- `method`: HTTP method to use (GET, POST, PUT, DELETE)
- `headers`: HTTP headers as JSON object
- `body`: Request body as JSON
- `timeout`: Request timeout in seconds
- `output_mapping`: Mapping of response fields to process variables

### Logger Service Task

The Logger service task allows processes to log messages at different levels during execution.

**Properties:**
- `level`: Log level (info, warning, error, debug)
- `message`: Message to log (required)
- `include_variables`: Whether to include process variables in the log
- `variable_filter`: Comma-separated list of variable names to include

## Creating Custom Service Tasks

You can extend Pythmata with your own custom service tasks by following these steps:

### Step 1: Create a Service Task Class

First, create a new Python class that inherits from the `ServiceTask` abstract base class:

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

### Step 2: Register Your Service Task

There are two main ways to register your service task:

#### Option 1: Register in a Module's `__init__.py`

Create a new module for your service tasks or use an existing one. In the module's `__init__.py` file:

```python
"""Custom service tasks."""

from pythmata.core.services.registry import get_service_task_registry
from your_module.your_file import MyCustomServiceTask

# Get the global registry
registry = get_service_task_registry()

# Register your service task
registry.register(MyCustomServiceTask)
```

#### Option 2: Register Programmatically at Startup

You can also register your service tasks programmatically at application startup:

```python
from pythmata.core.services.registry import get_service_task_registry
from your_module.your_file import MyCustomServiceTask

def register_service_tasks():
    """Register all custom service tasks."""
    registry = get_service_task_registry()
    registry.register(MyCustomServiceTask)
    # Register more tasks as needed

# Call this function during application startup
register_service_tasks()
```

### Step 3: Import Your Module

Make sure your module is imported when the application starts. For example, in your main application file:

```python
# Import your service tasks module to ensure registration
import your_module
```

## Example: Creating an Email Service Task

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

## Using Service Tasks in BPMN Diagrams

To use a service task in your BPMN diagram:

1. Add a service task to your diagram
2. Configure the service task with the appropriate properties:
   - Set the `taskName` property to the name of your registered service task
   - Configure the task-specific properties as needed

## Best Practices

1. **Unique Names**: Ensure your service task names are unique across the application.
2. **Clear Documentation**: Provide clear descriptions for your service task and its properties.
3. **Error Handling**: Implement robust error handling in your `execute` method.
4. **Asynchronous Operations**: Use `async/await` for any I/O operations to avoid blocking the process engine.
5. **Testing**: Write unit tests for your service tasks to ensure they work correctly.
6. **Security**: Be careful with sensitive information like passwords; consider using environment variables or a secure configuration store.
