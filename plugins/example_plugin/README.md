# Notification Service Task Plugin

This plugin provides a notification service task for Pythmata that allows sending notifications through various channels.

## Features

- Send notifications through multiple channels:
  - Email
  - SMS
  - Slack
  - Webhook
- Configure notification priority
- Support for message templates

## Installation

This plugin is automatically discovered and loaded by Pythmata when placed in the `plugins` directory.

## Usage

### In BPMN Diagrams

1. Add a service task to your BPMN diagram
2. Set the `taskName` property to `notification`
3. Configure the following properties:
   - `channel`: Notification channel (email, sms, slack, webhook)
   - `recipient`: Recipient of the notification
   - `subject`: Subject or title of the notification
   - `message`: Content of the notification
   - `priority`: Priority level (low, normal, high, urgent)
   - `template`: Optional template name for formatting

### Example Configuration

```json
{
  "taskName": "notification",
  "properties": {
    "channel": "email",
    "recipient": "user@example.com",
    "subject": "Order Confirmation",
    "message": "Your order #${orderId} has been confirmed.",
    "priority": "normal"
  }
}
```

## Dependencies

This plugin requires the following Python packages:
- requests>=2.28.0
- pyyaml>=6.0

## Development

To extend this plugin:

1. Modify `notification_task.py` to add new features
2. Update the `properties` method to add new configuration options
3. Enhance the `execute` method to implement the new functionality
4. Add any new dependencies to `requirements.txt`

## License

This plugin is licensed under the same license as Pythmata.
