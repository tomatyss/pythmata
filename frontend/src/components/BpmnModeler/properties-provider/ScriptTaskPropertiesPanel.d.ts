import React from 'react';

/**
 * Props for the ScriptTaskPropertiesPanel component
 */
export interface ScriptTaskPropertiesPanelProps {
  /**
   * The BPMN element being edited
   */
  element: BpmnElement;

  /**
   * The BPMN modeler instance
   */
  modeler: ExtendedBpmnModeler;
}

/**
 * A custom properties panel for script tasks that allows configuring
 * script content, language, and other script-related properties.
 */
declare const ScriptTaskPropertiesPanel: React.FC<ScriptTaskPropertiesPanelProps>;

export default ScriptTaskPropertiesPanel;
