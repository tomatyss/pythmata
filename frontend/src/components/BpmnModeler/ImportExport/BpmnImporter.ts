/**
 * BpmnImporter
 *
 * Utility for importing BPMN diagrams from standard BPMN files.
 * Handles the conversion of standard BPMN to Pythmata-specific extensions
 * and provides file upload and validation functionality.
 */

import {
  convertStandardToPythmata,
  validateBpmnXml,
} from './ExtensionConverter';

/**
 * Interface for the BPMN modeler instance
 */
interface BpmnModeler {
  importXML: (xml: string) => Promise<{ warnings: Array<string> }>;
}

/**
 * Result of a BPMN import operation
 */
export interface BpmnImportResult {
  success: boolean;
  xml?: string;
  error?: string;
  warnings?: Array<string>;
}

/**
 * Reads a file and returns its contents as a string
 *
 * @param file - The file to read
 * @returns Promise that resolves with the file contents
 */
const readFileAsText = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      if (event.target?.result) {
        resolve(event.target.result as string);
      } else {
        reject(new Error('Failed to read file'));
      }
    };
    reader.onerror = () => reject(new Error('Error reading file'));
    reader.readAsText(file);
  });
};

/**
 * Imports a BPMN file and loads it into the modeler
 *
 * @param file - The BPMN file to import
 * @param modeler - The BPMN modeler instance
 * @returns Promise that resolves with the import result
 */
export const importBpmnFile = async (
  file: File,
  modeler: BpmnModeler
): Promise<BpmnImportResult> => {
  try {
    // Check file extension
    if (
      !file.name.toLowerCase().endsWith('.bpmn') &&
      !file.name.toLowerCase().endsWith('.xml')
    ) {
      return {
        success: false,
        error: 'Invalid file type. Please upload a .bpmn or .xml file.',
      };
    }

    // Read file contents
    const xml = await readFileAsText(file);

    // Validate BPMN XML
    const validation = validateBpmnXml(xml);
    if (!validation.valid) {
      return {
        success: false,
        error: validation.error || 'Invalid BPMN XML',
      };
    }

    // Convert standard BPMN to Pythmata format
    const pythmataXml = convertStandardToPythmata(xml);

    // Import XML into modeler
    const result = await modeler.importXML(pythmataXml);

    return {
      success: true,
      xml: pythmataXml,
      warnings: result.warnings,
    };
  } catch (error) {
    console.error('Error importing BPMN:', error);
    return {
      success: false,
      error:
        error instanceof Error ? error.message : 'Unknown error importing BPMN',
    };
  }
};

/**
 * Parses a BPMN XML string and returns the process name if available
 *
 * @param xml - The BPMN XML to parse
 * @returns The process name or undefined if not found
 */
export const extractProcessNameFromBpmn = (xml: string): string | undefined => {
  try {
    // Look for process name in the XML
    const processMatch = xml.match(/<bpmn:process[^>]*name="([^"]+)"/);
    if (processMatch?.[1]) {
      return processMatch[1];
    }

    // If no named process found, look for process ID
    const processIdMatch = xml.match(/<bpmn:process[^>]*id="([^"]+)"/);
    if (processIdMatch?.[1]) {
      // Convert ID to a readable name (e.g., Process_1 -> Process 1)
      return processIdMatch[1].replace(/_/g, ' ');
    }

    return undefined;
  } catch (error) {
    console.error('Error extracting process name:', error);
    return undefined;
  }
};
