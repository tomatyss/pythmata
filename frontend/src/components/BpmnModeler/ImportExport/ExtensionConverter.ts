/**
 * ExtensionConverter
 *
 * Utility for converting between Pythmata extensions and standard BPMN.
 * Handles the conversion of custom Pythmata attributes to standard BPMN
 * and vice versa during import/export operations.
 */

/**
 * Converts Pythmata-specific extensions to standard BPMN format
 *
 * @param xml - The BPMN XML with Pythmata extensions
 * @returns The BPMN XML in standard format
 */
export const convertPythmataToStandard = (xml: string): string => {
  // Replace Pythmata namespace with standard BPMN namespace if needed
  let standardXml = xml;

  // Handle Pythmata service task configurations
  // This is a simplified version - actual implementation would need to handle
  // all Pythmata-specific extensions and convert them to standard attributes
  standardXml = standardXml.replace(
    /<pythmata:ServiceTaskConfig[\s\S]*?<\/pythmata:ServiceTaskConfig>/g,
    (match) => {
      // Extract task name and other properties
      const taskNameMatch = match.match(/taskName="([^"]+)"/);
      const taskName = taskNameMatch ? taskNameMatch[1] : '';

      // Convert to standard BPMN implementation attribute
      return `<!-- Converted from Pythmata extension: ${taskName} -->`;
    }
  );

  return standardXml;
};

/**
 * Converts standard BPMN format to include Pythmata extensions
 *
 * @param xml - The standard BPMN XML
 * @returns The BPMN XML with Pythmata extensions
 */
export const convertStandardToPythmata = (xml: string): string => {
  let pythmataXml = xml;

  // Add Pythmata namespace if it doesn't exist
  if (
    !pythmataXml.includes(
      'xmlns:pythmata="http://pythmata.org/schema/1.0/bpmn"'
    )
  ) {
    pythmataXml = pythmataXml.replace(
      /<bpmn:definitions/,
      '<bpmn:definitions xmlns:pythmata="http://pythmata.org/schema/1.0/bpmn"'
    );
  }

  // Handle standard BPMN service tasks and convert to Pythmata format
  // This is a simplified version - actual implementation would need to handle
  // all standard attributes and convert them to Pythmata extensions
  pythmataXml = pythmataXml.replace(
    /<bpmn:serviceTask([^>]*)>/g,
    (match, attributes) => {
      // Check if it already has Pythmata extensions
      if (match.includes('pythmata:')) {
        return match;
      }

      // Extract implementation attribute if it exists
      const implementationMatch = attributes.match(/implementation="([^"]+)"/);
      const implementation = implementationMatch ? implementationMatch[1] : '';

      // Add Pythmata extension
      return `${match}
        <bpmn:extensionElements>
          <pythmata:ServiceTaskConfig taskName="${implementation || 'defaultTask'}" />
        </bpmn:extensionElements>`;
    }
  );

  return pythmataXml;
};

/**
 * Validates if the given XML is a valid BPMN document
 *
 * @param xml - The BPMN XML to validate
 * @returns Object with validation result and optional error message
 */
export const validateBpmnXml = (
  xml: string
): { valid: boolean; error?: string } => {
  try {
    // Basic validation - check for required BPMN elements
    if (!xml.includes('<bpmn:definitions')) {
      return { valid: false, error: 'Missing BPMN definitions element' };
    }

    if (!xml.includes('<bpmn:process')) {
      return { valid: false, error: 'Missing BPMN process element' };
    }

    // More detailed validation could be added here

    return { valid: true };
  } catch (error) {
    return {
      valid: false,
      error:
        error instanceof Error ? error.message : 'Unknown validation error',
    };
  }
};
