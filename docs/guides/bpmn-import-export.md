# BPMN Import and Export

Pythmata supports importing and exporting BPMN diagrams, allowing you to share your process designs with other BPMN-compatible tools and import diagrams created in other tools.

## Exporting BPMN Diagrams

You can export your process diagrams as standard BPMN files (.bpmn) that can be opened in other BPMN modeling tools.

### How to Export a Diagram

1. Open the process designer for the diagram you want to export
2. In the toolbar, click the **Export** button
3. The diagram will be downloaded as a .bpmn file with the process name as the filename

### Export Format

The exported file is a standard BPMN 2.0 XML file that follows the BPMN specification. During export, Pythmata-specific extensions are converted to standard BPMN attributes where possible, ensuring maximum compatibility with other BPMN tools.

## Importing BPMN Diagrams

You can import BPMN diagrams created in other tools into Pythmata.

### How to Import a Diagram

1. Open the process designer
2. In the toolbar, click the **Import** button
3. In the import dialog, either:
   - Drag and drop a .bpmn or .xml file into the designated area
   - Click "Select File" to browse for a file
4. The imported diagram will be loaded into the modeler

### Import Validation

When importing a BPMN file, Pythmata performs validation to ensure the file is a valid BPMN diagram. If any issues are detected, you'll see an error message with details about the problem.

### Compatibility Notes

- Pythmata supports standard BPMN 2.0 files
- During import, standard BPMN attributes are converted to Pythmata-specific extensions where needed
- Some advanced features from other BPMN tools may not be fully supported
- Basic compatibility with Camunda BPMN is supported, but some Camunda-specific extensions may not be preserved

## Troubleshooting

### Export Issues

- If you encounter issues with the exported file not opening in other tools, try using the "Copy XML" button to get the raw XML and save it manually as a .bpmn file

### Import Issues

- If an import fails with a validation error, check that the file is a valid BPMN 2.0 XML file
- Some BPMN tools may use non-standard extensions that Pythmata doesn't recognize
- If you're importing a file with custom extensions, you may need to modify the XML manually to remove or adapt those extensions

## Best Practices

- When sharing diagrams between different BPMN tools, focus on the core BPMN elements and avoid tool-specific extensions
- Always validate imported diagrams to ensure they work as expected in Pythmata
- Consider using the XML editor tab to make manual adjustments to imported diagrams if needed
- Save your work before importing a new diagram to avoid losing changes
