import { useState } from 'react';
import {
  Box,
  Tab,
  Tabs,
  Typography,
  Checkbox,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from '@mui/material';
import ProcessDiagramViewer from '../ProcessDiagramViewer/ProcessDiagramViewer';

interface ProcessInstance {
  id: string;
  startDate: string;
  endDate?: string;
  state: string;
  version: string;
  parentInstanceId?: string;
}

interface TokenData {
  nodeId: string;
  state: string;
  scopeId?: string;
  data?: Record<string, unknown>;
}

interface ProcessViewProps {
  bpmnXml: string;
  instances: ProcessInstance[];
  tokens: TokenData[];
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

/**
 * A panel component for tab content
 */
function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`process-tabpanel-${index}`}
      aria-labelledby={`process-tab-${index}`}
      {...other}
      style={{ height: '100%' }}
    >
      {value === index && <Box sx={{ height: '100%' }}>{children}</Box>}
    </div>
  );
}

/**
 * A component that displays process definition and instances in a tabbed view
 * @param props Component properties including BPMN XML and instance data
 * @returns ProcessView component
 */
const ProcessView = ({ bpmnXml, instances, tokens }: ProcessViewProps) => {
  const [tabValue, setTabValue] = useState(1); // Start on ACTIVE INSTANCES tab
  const [selectedInstances, setSelectedInstances] = useState<Set<string>>(
    new Set()
  );

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      setSelectedInstances(new Set(instances.map((i) => i.id)));
    } else {
      setSelectedInstances(new Set());
    }
  };

  const handleSelectInstance = (id: string) => {
    const newSelected = new Set(selectedInstances);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedInstances(newSelected);
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="DEFINITION" />
          <Tab label={`ACTIVE INSTANCES (${instances.length})`} />
        </Tabs>
      </Box>

      <TabPanel value={tabValue} index={0}>
        <ProcessDiagramViewer bpmnXml={bpmnXml} tokens={[]} />
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ mb: 2 }}>
            <select
              value={
                selectedInstances.size === 1
                  ? Array.from(selectedInstances)[0]
                  : ''
              }
              onChange={(e) => {
                if (e.target.value) {
                  setSelectedInstances(new Set([e.target.value]));
                } else {
                  setSelectedInstances(new Set());
                }
              }}
              style={{
                width: '100%',
                padding: '8px',
                marginBottom: '16px',
                borderRadius: '4px',
                border: '1px solid #ddd',
              }}
            >
              <option value="">Select instance</option>
              {instances.map((instance) => (
                <option key={instance.id} value={instance.id}>
                  {instance.id}
                </option>
              ))}
            </select>

            <ProcessDiagramViewer bpmnXml={bpmnXml} tokens={tokens} />
          </Box>

          <Box>
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              Process Instances ({instances.length} results found)
            </Typography>

            <TableContainer
              component={Paper}
              variant="outlined"
              sx={{ maxHeight: 400 }}
            >
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell padding="checkbox">
                      <Checkbox
                        indeterminate={
                          selectedInstances.size > 0 &&
                          selectedInstances.size < instances.length
                        }
                        checked={
                          instances.length > 0 &&
                          selectedInstances.size === instances.length
                        }
                        onChange={handleSelectAll}
                      />
                    </TableCell>
                    <TableCell>Instance ID</TableCell>
                    <TableCell>Version</TableCell>
                    <TableCell>Start Date</TableCell>
                    <TableCell>End Date</TableCell>
                    <TableCell>Parent Instance</TableCell>
                    <TableCell align="right">Operations</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {instances.map((instance) => (
                    <TableRow
                      key={instance.id}
                      hover
                      selected={selectedInstances.has(instance.id)}
                      onClick={() => handleSelectInstance(instance.id)}
                      sx={{ cursor: 'pointer' }}
                    >
                      <TableCell padding="checkbox">
                        <Checkbox
                          checked={selectedInstances.has(instance.id)}
                          onChange={() => handleSelectInstance(instance.id)}
                        />
                      </TableCell>
                      <TableCell>{instance.id}</TableCell>
                      <TableCell>{instance.version}</TableCell>
                      <TableCell>
                        {new Date(instance.startDate).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        {instance.endDate
                          ? new Date(instance.endDate).toLocaleString()
                          : '--'}
                      </TableCell>
                      <TableCell>
                        {instance.parentInstanceId || 'None'}
                      </TableCell>
                      <TableCell align="right">
                        {/* Add operation buttons here if needed */}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        </Box>
      </TabPanel>
    </Box>
  );
};

export default ProcessView;
