import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import apiService from '@/services/api';
import ProcessDiagramViewer from '@/components/shared/ProcessDiagramViewer';
import {
  Box,
  Card,
  CardContent,
  Typography,
  CircularProgress,
} from '@mui/material';

interface ProcessDetails {
  name: string;
  bpmn_xml: string;
}

const ProcessDiagram = () => {
  const { id } = useParams();
  const [loading, setLoading] = useState(true);
  const [process, setProcess] = useState<ProcessDetails | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProcess = async () => {
      if (!id) {
        setError('Process ID is missing');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        console.warn('Fetching process definition:', id);

        const response = await apiService.getProcessDefinition(id);
        console.warn('Process definition response:', response);

        if (!response.data.bpmn_xml) {
          throw new Error('Process definition has no BPMN XML');
        }

        setProcess({
          name: response.data.name,
          bpmn_xml: response.data.bpmn_xml,
        });
      } catch (error) {
        console.error('Failed to fetch process:', error);
        setError(
          error instanceof Error
            ? error.message
            : 'Failed to load process diagram. Please try again.'
        );
      } finally {
        setLoading(false);
      }
    };

    fetchProcess();
  }, [id]);

  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '400px',
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error || !process) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '400px',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        <Typography color="error" variant="h6">
          {error || 'Failed to load process diagram'}
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        {process.name}
      </Typography>

      <Card>
        <CardContent>
          <Box sx={{ height: '600px' }}>
            <ProcessDiagramViewer
              bpmnXml={process.bpmn_xml}
              key={process.bpmn_xml} // Force re-render when XML changes
            />
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default ProcessDiagram;
