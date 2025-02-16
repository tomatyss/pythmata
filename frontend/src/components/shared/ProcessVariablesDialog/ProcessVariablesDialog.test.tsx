import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ProcessVariablesDialog from './ProcessVariablesDialog';

describe('ProcessVariablesDialog', () => {
  const mockOnClose = vi.fn();
  const mockOnSubmit = vi.fn();
  const mockProcessId = 'test-process';
  const mockVariableDefinitions = [
    {
      name: 'amount',
      type: 'number' as const,
      required: true,
      label: 'Amount',
      validation: {
        min: 0,
      },
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dialog when open', () => {
    render(
      <ProcessVariablesDialog
        open={true}
        processId={mockProcessId}
        variableDefinitions={mockVariableDefinitions}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    expect(screen.getByText('Start Process')).toBeInTheDocument();
    expect(screen.getByLabelText('Amount')).toBeInTheDocument();
  });

  it('validates amount input', () => {
    render(
      <ProcessVariablesDialog
        open={true}
        processId={mockProcessId}
        variableDefinitions={mockVariableDefinitions}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    // Try submitting with invalid amount
    fireEvent.change(screen.getByLabelText('Amount'), {
      target: { value: '-1' },
    });
    fireEvent.click(screen.getByText('Start'));

    expect(screen.getByText('Value must be at least 0')).toBeInTheDocument();
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('submits valid form data', () => {
    render(
      <ProcessVariablesDialog
        open={true}
        processId={mockProcessId}
        variableDefinitions={mockVariableDefinitions}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    // Enter valid amount
    fireEvent.change(screen.getByLabelText('Amount'), {
      target: { value: '99.99' },
    });
    fireEvent.click(screen.getByText('Start'));

    expect(mockOnSubmit).toHaveBeenCalledWith({
      amount: {
        type: 'number',
        value: 99.99,
      },
    });
  });

  it('closes dialog on cancel', () => {
    render(
      <ProcessVariablesDialog
        open={true}
        processId={mockProcessId}
        variableDefinitions={mockVariableDefinitions}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    fireEvent.click(screen.getByText('Cancel'));
    expect(mockOnClose).toHaveBeenCalled();
  });

  it('resets form on close', () => {
    const { rerender } = render(
      <ProcessVariablesDialog
        open={true}
        processId={mockProcessId}
        variableDefinitions={mockVariableDefinitions}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    // Enter amount
    const amountInput = screen.getByLabelText('Amount');
    fireEvent.change(amountInput, { target: { value: '99.99' } });
    expect(amountInput).toHaveValue(99.99);

    // Close dialog
    rerender(
      <ProcessVariablesDialog
        open={false}
        processId={mockProcessId}
        variableDefinitions={mockVariableDefinitions}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    // Reopen dialog
    rerender(
      <ProcessVariablesDialog
        open={true}
        processId={mockProcessId}
        variableDefinitions={mockVariableDefinitions}
        onClose={mockOnClose}
        onSubmit={mockOnSubmit}
      />
    );

    // Amount should be reset
    expect(screen.getByLabelText('Amount')).toHaveValue(null);
  });
});
