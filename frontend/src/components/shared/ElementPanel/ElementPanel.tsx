import React from 'react';
import { Box, Typography, IconButton, Alert, Button } from '@mui/material';
import { Close as CloseIcon } from '@mui/icons-material';
// @ts-expect-error - Missing type definitions for the JSX component
import ElementPropertiesPanel from '@/components/BpmnModeler/properties-provider/ElementPropertiesPanel';
import BpmnModeler from 'bpmn-js/lib/Modeler';

// Define types for BPMN elements and properties
interface BusinessObject {
  extensionElements?: {
    values: ExtensionElement[];
  };
}

interface BpmnElement {
  id: string;
  type: string;
  businessObject: BusinessObject;
}

// Define types for the modeler modules
interface ElementRegistry {
  get(id: string): BpmnElement;
}

interface Modeling {
  updateProperties(
    element: BpmnElement,
    properties: Record<string, unknown>
  ): void;
}

interface Moddle {
  create<T>(type: string, properties?: Record<string, unknown>): T;
}

interface EventBus {
  on<T = unknown>(event: string, callback: (event: T) => void): void;
}

// Define a mapping of module names to their types
interface ModuleTypeMap {
  elementRegistry: ElementRegistry;
  modeling: Modeling;
  moddle: Moddle;
  eventBus: EventBus;
}

// Define a type for the modeler with the methods we need
type ModelerModule = keyof ModuleTypeMap;

// Export this type for use in tests
export type ExtendedBpmnModeler = BpmnModeler & {
  get<T extends ModelerModule>(name: T): ModuleTypeMap[T];
};

// Define types for extension elements
interface ExtensionElement {
  $type: string;
  taskName?: string;
  properties?: {
    values: PropertyValue[];
  };
}

interface PropertyValue {
  name: string;
  value: string;
}

interface ElementPanelProps {
  elementId: string;
  modeler: ExtendedBpmnModeler;
  onClose: () => void;
}

/**
 * Element Panel
 *
 * A panel for editing properties of any BPMN element.
 *
 * @param {Object} props - Component props
 * @param {string} props.elementId - The ID of the BPMN element
 * @param {Object} props.modeler - The BPMN modeler instance
 * @param {Function} props.onClose - Function to close the panel
 */
const ElementPanel: React.FC<ElementPanelProps> = ({
  elementId,
  modeler,
  onClose,
}) => {
  const [error, setError] = React.useState<string | null>(null);
  const [element, setElement] = React.useState<BpmnElement | null>(null);

  // Get current element
  React.useEffect(() => {
    if (!modeler || !elementId) return;

    try {
      const elementRegistry = modeler.get('elementRegistry');
      const element = elementRegistry.get(elementId);

      if (!element) {
        setError(`Element with ID ${elementId} not found`);
        return;
      }

      setElement(element);
    } catch (error) {
      console.error('Error getting element:', error);
      setError('Failed to load element configuration');
    }
  }, [modeler, elementId]);

  // Get element type name for display
  const getElementTypeName = (type: string): string => {
    if (!type) return 'Element';

    // Remove 'bpmn:' prefix
    const typeName = type.replace('bpmn:', '');

    // Add spaces between camel case words
    return typeName.replace(/([A-Z])/g, ' $1').trim();
  };

  const [saving, setSaving] = React.useState(false);
  const elementPropertiesPanelRef = React.useRef<{
    saveScript?: () => void;
  }>(null);

  // Handle save
  const handleSave = () => {
    setSaving(true);

    // Try to call saveScript on the ScriptTaskPropertiesPanel if it's a script task
    if (
      element?.type === 'bpmn:ScriptTask' &&
      elementPropertiesPanelRef.current?.saveScript
    ) {
      try {
        elementPropertiesPanelRef.current.saveScript();
        // Wait a moment to show the saving state
        setTimeout(() => {
          setSaving(false);
          onClose();
        }, 500);
      } catch (error) {
        console.error('Error saving script:', error);
        setSaving(false);
        onClose();
      }
    } else {
      // For other element types, just close the panel
      setSaving(false);
      onClose();
    }
  };

  return (
    <Box sx={{ p: 2 }}>
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 2,
        }}
      >
        <Typography variant="h6">
          {element ? getElementTypeName(element.type) : 'Element'} Properties
        </Typography>
        <IconButton onClick={onClose} aria-label="close">
          <CloseIcon />
        </IconButton>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {element && (
        <>
          <ElementPropertiesPanel
            ref={elementPropertiesPanelRef}
            element={element}
            modeler={modeler}
          />

          <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              variant="contained"
              onClick={handleSave}
              disabled={saving}
              data-testid="save-element"
            >
              {saving ? 'Saving...' : 'Save'}
            </Button>
          </Box>
        </>
      )}
    </Box>
  );
};

export default ElementPanel;
