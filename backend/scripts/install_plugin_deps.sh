#!/bin/bash
# Script to install dependencies for plugins

PLUGIN_DIR=${PYTHMATA_PLUGIN_DIR:-"/app/plugins"}
echo "Checking for plugin dependencies in $PLUGIN_DIR"

if [ ! -d "$PLUGIN_DIR" ]; then
  echo "Plugin directory not found: $PLUGIN_DIR"
  exit 0
fi

# Process each plugin directory
for plugin_dir in "$PLUGIN_DIR"/*/; do
  if [ -d "$plugin_dir" ]; then
    plugin_name=$(basename "$plugin_dir")
    echo "Processing plugin: $plugin_name"
    
    # Check for requirements.txt
    if [ -f "${plugin_dir}requirements.txt" ]; then
      echo "Installing dependencies for $plugin_name"
      pip install -r "${plugin_dir}requirements.txt"
      if [ $? -ne 0 ]; then
        echo "Warning: Failed to install some dependencies for $plugin_name"
      fi
    else
      echo "No requirements.txt found for $plugin_name"
    fi
  fi
done

echo "Plugin dependency installation complete"
