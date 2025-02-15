import { useEffect, useRef, useState } from 'react';
import BpmnJS from 'bpmn-js';
import 'bpmn-js/dist/assets/diagram-js.css';
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn.css';
import { Box } from '@mui/material';

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

// Group tokens by nodeId for counting
const groupTokensByNode = (tokens: TokenData[]) => {
  return tokens.reduce(
    (acc, token) => {
      const nodeGroup = acc[token.nodeId] || {
        count: 0,
        states: new Set<string>(),
        tokens: [],
      };

      acc[token.nodeId] = {
        count: nodeGroup.count + 1,
        states: nodeGroup.states.add(token.state),
        tokens: [...nodeGroup.tokens, token],
      };

      return acc;
    },
    {} as Record<
      string,
      { count: number; states: Set<string>; tokens: TokenData[] }
    >
  );
};

// Get token style based on state
const getTokenStyle = (states: Set<string>) => {
  if (states.has('error')) {
    return {
      backgroundColor: '#dc3545', // Red for error
      boxShadow: '0 2px 4px rgba(220,53,69,0.3)',
    };
  }
  if (states.has('async')) {
    return {
      backgroundColor: '#ffc107', // Yellow for async
      boxShadow: '0 2px 4px rgba(255,193,7,0.3)',
    };
  }
  return {
    backgroundColor: '#4CAF50', // Green for active/default
    boxShadow: '0 2px 4px rgba(76,175,80,0.3)',
  };
};

const ProcessDiagramViewer = ({
  bpmnXml,
  className,
  tokens = [],
}: ProcessDiagramViewerProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [viewer, setViewer] = useState<BpmnJS | null>(null);

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

    console.warn('Importing BPMN XML:', bpmnXml.substring(0, 100) + '...');

    // Import BPMN diagram
    viewer
      .importXML(bpmnXml)
      .then(() => {
        console.warn('BPMN XML imported successfully');
        const canvas = viewer.get('canvas');
        canvas.zoom('fit-viewport');
      })
      .catch((err: Error) => {
        console.error('Error rendering BPMN diagram:', err);
        throw err; // Re-throw to trigger error boundary
      });
  }, [viewer, bpmnXml]);

  useEffect(() => {
    // Cleanup function to destroy viewer when component unmounts
    return () => {
      if (viewer) {
        try {
          viewer.destroy();
        } catch (err) {
          console.error('Error destroying viewer:', err);
        }
      }
    };
  }, [viewer]);

  useEffect(() => {
    if (!viewer || !tokens.length) return;

    const overlays = viewer.get('overlays');

    // Clear existing overlays
    overlays.clear();

    // Group tokens by node for counting
    const tokenGroups = groupTokensByNode(tokens);

    // Add token overlays with counts and tooltips
    Object.entries(tokenGroups).forEach(([nodeId, group]) => {
      const style = getTokenStyle(group.states);

      overlays.add(nodeId, {
        position: {
          top: -10,
          left: -10,
        },
        html: `
          <div
            class="token-overlay"
            style="
              width: ${group.count > 1 ? '25px' : '20px'};
              height: ${group.count > 1 ? '25px' : '20px'};
              background-color: ${style.backgroundColor};
              border-radius: 50%;
              display: flex;
              align-items: center;
              justify-content: center;
              color: white;
              font-size: 12px;
              font-weight: bold;
              box-shadow: ${style.boxShadow};
              cursor: pointer;
              transition: transform 0.2s;
            "
            title="${group.count} token${group.count > 1 ? 's' : ''} (${Array.from(group.states).join(', ')})"
          >
            ${group.count > 1 ? group.count : ''}
          </div>
        `,
      });
    });
  }, [viewer, tokens]);

  return (
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
          },
        },
      }}
    />
  );
};

export default ProcessDiagramViewer;
