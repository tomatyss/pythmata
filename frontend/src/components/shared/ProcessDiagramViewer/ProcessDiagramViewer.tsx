import { useEffect, useRef, useState, useCallback } from 'react';
import BpmnJS, { ModdleElement } from 'bpmn-js';
import 'bpmn-js/dist/assets/diagram-js.css';
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn.css';
import { Box } from '@mui/material';
import TokenInspectorDialog from '../TokenInspectorDialog/TokenInspectorDialog';

interface TokenData {
  nodeId: string;
  state: string;
  scopeId?: string;
  data?: Record<string, unknown>;
}

interface ProcessDiagramViewerProps {
  bpmnXml: string;
  className?: string;
  tokens?: TokenData[];
}

// Define BPMN viewer types
interface ElementRegistry {
  get: (id: string) => BpmnElement;
  getAll: () => BpmnElement[];
  getGraphics: (id: string) => SVGGraphicsElement;
}

// Define types for BPMN elements
interface BpmnElement extends ModdleElement {
  id: string;
  type: string;
  businessObject: {
    id: string;
    $type: string;
    [key: string]: unknown;
  };
  parent?: BpmnElement;
  incoming?: BpmnFlow[];
  outgoing?: BpmnFlow[];
}

interface BpmnFlow {
  id: string;
  type: string;
  businessObject: {
    id: string;
    $type: string;
    sourceRef: { id: string };
    targetRef: { id: string };
  };
}

// Group tokens by nodeId for counting across all instances
const groupTokensByNode = (tokens: TokenData[]) => {
  const groups = tokens.reduce(
    (acc, token) => {
      const nodeGroup = acc[token.nodeId] || {
        count: 0,
        tokens: [],
      };

      acc[token.nodeId] = {
        count: nodeGroup.count + 1,
        tokens: [...nodeGroup.tokens, token],
      };

      return acc;
    },
    {} as Record<string, { count: number; tokens: TokenData[] }>
  );

  return groups;
};

// Function to find matching node ID in the diagram
const findMatchingNodeId = (
  elementRegistry: ElementRegistry,
  nodeId: string
): string | null => {
  const elements = elementRegistry.getAll();

  // First try exact match
  const exactMatch = elements.find((el) => el.id === nodeId);
  if (exactMatch) return exactMatch.id;

  // Try matching by business object ID
  const businessObjectMatch = elements.find(
    (el) => el.businessObject?.id === nodeId
  );
  if (businessObjectMatch) return businessObjectMatch.id;

  // Try matching by type (e.g., if looking for StartEvent_1, match any start event)
  if (nodeId.includes('Start')) {
    const startEvent = elements.find((el) => el.type === 'bpmn:StartEvent');
    if (startEvent) return startEvent.id;
  } else if (nodeId.includes('Task')) {
    const task = elements.find((el) => el.type === 'bpmn:Task');
    if (task) return task.id;
  } else if (nodeId.includes('End')) {
    const endEvent = elements.find((el) => el.type === 'bpmn:EndEvent');
    if (endEvent) return endEvent.id;
  }

  return null;
};

const ProcessDiagramViewer = ({
  bpmnXml,
  className,
  tokens = [],
}: ProcessDiagramViewerProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [viewer, setViewer] = useState<BpmnJS | null>(null);
  const [selectedTokens, setSelectedTokens] = useState<TokenData[]>([]);
  const [currentTokenIndex, setCurrentTokenIndex] = useState(0);
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;

    // Initialize BPMN viewer
    const bpmnViewer = new BpmnJS({
      container: containerRef.current,
    });

    setViewer(bpmnViewer);

    return () => {
      bpmnViewer.destroy();
    };
  }, []);

  useEffect(() => {
    if (!viewer || !bpmnXml) return;

    // Import BPMN diagram
    viewer
      .importXML(bpmnXml)
      .then(() => {
        const canvas = viewer.get('canvas');
        canvas.zoom('fit-viewport');
      })
      .catch((err: Error) => {
        console.error('Error rendering BPMN diagram:', err);
        throw err; // Re-throw to trigger error boundary
      });
  }, [viewer, bpmnXml]);

  const handleTokenClick = useCallback((nodeTokens: TokenData[]) => {
    setSelectedTokens(nodeTokens);
    setCurrentTokenIndex(0);
    setIsInspectorOpen(true);
  }, []);

  const handleNavigateToken = useCallback((index: number) => {
    setCurrentTokenIndex(index);
  }, []);

  useEffect(() => {
    if (!viewer || !tokens.length) return;

    const overlays = viewer.get('overlays');
    const elementRegistry = viewer.get('elementRegistry') as ElementRegistry;

    // Clear existing overlays
    overlays.clear();

    // Group tokens by node for counting
    const tokenGroups = groupTokensByNode(tokens);

    // Add token overlays with counts and tooltips
    Object.entries(tokenGroups).forEach(([nodeId, group]) => {
      // Find matching node ID in the diagram
      const matchingNodeId = findMatchingNodeId(elementRegistry, nodeId);

      if (!matchingNodeId) {
        console.error(`No matching node found for ${nodeId}`);
        return;
      }

      const element = elementRegistry.get(matchingNodeId);
      if (!element) {
        console.error(`Element not found for matched ID ${matchingNodeId}`);
        return;
      }

      // Get element dimensions from the viewer
      const elementGfx = elementRegistry.getGraphics(matchingNodeId);
      const elementBox = elementGfx.getBBox();

      // Add Camunda-style token count overlay
      overlays.add(matchingNodeId, {
        position: {
          top: elementBox.height - 15,
          left: elementBox.width - 15,
        },
        html: `
          <div
            class="token-overlay"
            data-node-id="${nodeId}"
            style="
              min-width: 25px;
              height: 25px;
              padding: 0 5px;
              background-color: white;
              border: 2px solid #dc3545;
              border-radius: 12px;
              display: flex;
              align-items: center;
              justify-content: center;
              color: #dc3545;
              font-size: 12px;
              font-weight: bold;
              cursor: pointer;
              transition: transform 0.2s, background-color 0.2s;
              z-index: 1000;
            "
            title="Total tokens at this node: ${group.count}"
          >
            ${group.count}
          </div>
        `,
      });

      // Add click event listener
      const overlay = document.querySelector(`[data-node-id="${nodeId}"]`);
      if (overlay) {
        overlay.addEventListener('click', () => handleTokenClick(group.tokens));
      }
    });

    // Cleanup function to remove event listeners
    return () => {
      Object.keys(tokenGroups).forEach((nodeId) => {
        const overlay = document.querySelector(`[data-node-id="${nodeId}"]`);
        const group = tokenGroups[nodeId];
        if (overlay && group) {
          overlay.removeEventListener('click', () =>
            handleTokenClick(group.tokens)
          );
        }
      });
    };
  }, [viewer, tokens, bpmnXml, handleTokenClick]);

  return (
    <>
      <Box
        ref={containerRef}
        className={className}
        sx={{
          height: '100%',
          minHeight: '400px',
          border: '1px solid #ddd',
          borderRadius: 1,
          '& .djs-overlay': {
            position: 'absolute',
          },
          '& .token-overlay': {
            pointerEvents: 'auto',
            '&:hover': {
              transform: 'scale(1.1)',
              backgroundColor: '#f8f9fa',
            },
          },
        }}
      />

      <TokenInspectorDialog
        open={isInspectorOpen}
        onClose={() => setIsInspectorOpen(false)}
        tokens={selectedTokens}
        currentTokenIndex={currentTokenIndex}
        onNavigateToken={handleNavigateToken}
      />
    </>
  );
};

export default ProcessDiagramViewer;
