import { useEffect, useRef, useState } from 'react';
import BpmnJS from 'bpmn-js';
import 'bpmn-js/dist/assets/diagram-js.css';
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn.css';
import { Box } from '@mui/material';

interface ProcessDiagramViewerProps {
  bpmnXml: string;
  className?: string;
  tokens?: Array<{
    nodeId: string;
    state: string;
    scopeId?: string;
  }>;
}

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

    // Add token overlays
    tokens.forEach((token) => {
      overlays.add(token.nodeId, {
        position: {
          top: -10,
          left: -10,
        },
        html: `
          <div
            style="
              width: 20px;
              height: 20px;
              background-color: #4CAF50;
              border-radius: 50%;
              display: flex;
              align-items: center;
              justify-content: center;
              color: white;
              font-size: 12px;
              font-weight: bold;
              box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            "
          ></div>
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
          pointerEvents: 'none',
        },
      }}
    />
  );
};

export default ProcessDiagramViewer;
