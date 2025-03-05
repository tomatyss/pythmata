import React from 'react';

interface SequenceFlowPropertiesPanelProps {
  element: unknown;
  modeler: unknown;
  variables?: Array<{
    name: string;
    type?: string;
    [key: string]: unknown;
  }>;
}

declare const SequenceFlowPropertiesPanel: React.FC<SequenceFlowPropertiesPanelProps>;

export default SequenceFlowPropertiesPanel;
