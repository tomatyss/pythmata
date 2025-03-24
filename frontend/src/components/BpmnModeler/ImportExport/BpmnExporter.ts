/**
 * BpmnExporter
 *
 * Utility for exporting BPMN diagrams to standard BPMN files.
 * Handles the conversion of Pythmata-specific extensions to standard BPMN
 * and provides file download functionality.
 */

import { convertPythmataToStandard } from './ExtensionConverter';

/**
 * Interface for the BPMN modeler instance
 */
interface BpmnModeler {
  saveXML: (options?: { format?: boolean }) => Promise<{ xml: string }>;
}

/**
 * Exports the current BPMN diagram as a standard BPMN file
 *
 * @param modeler - The BPMN modeler instance
 * @param processName - The name of the process (used for the filename)
 * @returns Promise that resolves when the export is complete
 */
export const exportAsBpmn = async (
  modeler: BpmnModeler,
  processName: string
): Promise<void> => {
  try {
    // Get the XML from the modeler
    const { xml } = await modeler.saveXML({ format: true });

    // Convert Pythmata extensions to standard BPMN
    const standardXml = convertPythmataToStandard(xml);

    // Create a blob with the XML content
    const blob = new Blob([standardXml], { type: 'application/xml' });

    // Create a download link
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;

    // Generate a filename based on the process name
    const filename = `${processName.replace(/\s+/g, '_').toLowerCase()}.bpmn`;
    link.download = filename;

    // Trigger the download
    document.body.appendChild(link);
    link.click();

    // Clean up
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Error exporting BPMN:', error);
    throw new Error(
      `Failed to export BPMN: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
};

/**
 * Exports the current BPMN diagram as a standard BPMN file with custom filename
 *
 * @param xml - The BPMN XML content
 * @param filename - The filename to use for the download
 * @returns Promise that resolves when the export is complete
 */
export const exportXmlAsBpmn = (xml: string, filename: string): void => {
  try {
    // Convert Pythmata extensions to standard BPMN
    const standardXml = convertPythmataToStandard(xml);

    // Create a blob with the XML content
    const blob = new Blob([standardXml], { type: 'application/xml' });

    // Create a download link
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;

    // Ensure filename has .bpmn extension
    const finalFilename = filename.endsWith('.bpmn')
      ? filename
      : `${filename}.bpmn`;
    link.download = finalFilename;

    // Trigger the download
    document.body.appendChild(link);
    link.click();

    // Clean up
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Error exporting BPMN:', error);
    throw new Error(
      `Failed to export BPMN: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
};
