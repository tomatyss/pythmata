# Pythmata Plugins

This directory contains plugins for the Pythmata workflow engine. Plugins extend Pythmata with custom service tasks and other functionality.

## Plugin Directory Structure

Each plugin should be placed in its own subdirectory with the following structure:

```
plugins/
├── my_plugin/
│   ├── __init__.py          # Plugin initialization and registration
│   ├── requirements.txt     # Optional dependencies
│   ├── README.md            # Plugin documentation
│   └── my_task.py           # Service task implementation
└── another_plugin/
    ├── __init__.py
    └── ...
```

## Available Plugins

### Example Plugin

The `example_plugin` directory contains a sample plugin that demonstrates how to create custom service tasks. It provides a notification service task that can send notifications through various channels.

## Creating Your Own Plugins

To create your own plugin:

1. Create a new directory in the `plugins` directory
2. Implement your service task(s) in Python files
3. Create an `__init__.py` file that registers your service tasks
4. Add a `requirements.txt` file if your plugin has dependencies
5. Add a `README.md` file to document your plugin

For detailed instructions, see the [Custom Service Tasks](../docs/reference/bpmn/custom-service-tasks.md) documentation.

## Plugin Discovery

Plugins are automatically discovered and loaded at startup from the `plugins` directory. The plugin discovery process:

1. Scans the `plugins` directory for subdirectories containing `__init__.py` files
2. Imports each plugin package
3. Registers service tasks defined in the plugin

## Plugin Dependencies

If your plugin requires additional Python packages, list them in a `requirements.txt` file in your plugin directory. These dependencies will be automatically installed when Pythmata starts with the `PYTHMATA_INSTALL_PLUGIN_DEPS=true` environment variable set.

## Best Practices

1. Use unique names for your service tasks to avoid conflicts
2. Document your service tasks and their properties
3. Handle errors gracefully in your service task implementations
4. Use asynchronous code for I/O operations
5. Write tests for your plugins
