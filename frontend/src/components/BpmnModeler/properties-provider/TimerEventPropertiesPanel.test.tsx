import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import '@testing-library/jest-dom';
import TimerEventPropertiesPanel from './TimerEventPropertiesPanel';

// Mock data
const mockElement = {
  id: 'TimerEvent_1',
  type: 'bpmn:StartEvent',
  businessObject: {
    id: 'TimerEvent_1',
    eventDefinitions: [
      {
        $type: 'bpmn:TimerEventDefinition',
        timeDuration: { body: 'PT1H' }
      }
    ]
  }
};

// Mock modeler
const mockModeler = {
  get: vi.fn().mockImplementation((module) => {
    if (module === 'modeling') {
      return {
        updateProperties: vi.fn()
      };
    }
    if (module === 'moddle') {
      return {
        create: vi.fn().mockImplementation((type, props) => ({
          $type: type,
          ...props
        }))
      };
    }
    return {};
  })
};

describe('TimerEventPropertiesPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders timer type and value inputs', () => {
    render(
      <TimerEventPropertiesPanel element={mockElement} modeler={mockModeler} />
    );
    
    // Check if timer type dropdown is rendered
    expect(screen.getByLabelText(/Timer Type/i)).toBeInTheDocument();
    
    // Check if timer value input is rendered
    expect(screen.getByLabelText(/Timer Value/i)).toBeInTheDocument();
    
    // Check if the initial value is set correctly
    expect(screen.getByLabelText(/Timer Value/i)).toHaveValue('PT1H');
  });
  
  it('changes timer type correctly', async () => {
    render(
      <TimerEventPropertiesPanel element={mockElement} modeler={mockModeler} />
    );
    
    // Get the timer type dropdown
    const timerTypeSelect = screen.getByLabelText(/Timer Type/i);
    
    // Change timer type to date
    fireEvent.mouseDown(timerTypeSelect);
    
    // Wait for dropdown options to appear
    await waitFor(() => {
      expect(screen.getByText('Date')).toBeInTheDocument();
    });
    
    // Click on the "Date" option
    fireEvent.click(screen.getByText('Date'));
    
    // Check if the timer value is reset
    expect(screen.getByLabelText(/Timer Value/i)).toHaveValue('');
    
    // Check if the placeholder text is updated
    expect(screen.getByPlaceholderText(/e\.g\., 2025-03-15T09:00:00/i)).toBeInTheDocument();
  });
  
  it('updates timer value correctly', () => {
    render(
      <TimerEventPropertiesPanel element={mockElement} modeler={mockModeler} />
    );
    
    // Get the timer value input
    const timerValueInput = screen.getByLabelText(/Timer Value/i);
    
    // Change timer value
    fireEvent.change(timerValueInput, { target: { value: 'PT2H30M' } });
    
    // Check if the timer value is updated
    expect(timerValueInput).toHaveValue('PT2H30M');
    
    // Verify that the modeling.updateProperties was called
    const modeling = mockModeler.get('modeling');
    expect(modeling.updateProperties).toHaveBeenCalled();
  });
  
  it('handles element with extension elements correctly', () => {
    const elementWithExtensions = {
      id: 'TimerEvent_2',
      type: 'bpmn:StartEvent',
      businessObject: {
        id: 'TimerEvent_2',
        extensionElements: {
          values: [
            {
              $type: 'pythmata:TimerEventConfig',
              timerType: 'cycle',
              timerValue: 'R3/PT1H'
            }
          ]
        }
      }
    };
    
    render(
      <TimerEventPropertiesPanel element={elementWithExtensions} modeler={mockModeler} />
    );
    
    // Check if the timer type is set from extension elements
    expect(screen.getByLabelText(/Timer Type/i)).toHaveValue('cycle');
    
    // Check if the timer value is set from extension elements
    expect(screen.getByLabelText(/Timer Value/i)).toHaveValue('R3/PT1H');
  });
});
