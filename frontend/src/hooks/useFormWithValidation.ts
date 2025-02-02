import { useForm, UseFormProps, FieldValues } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { VALIDATION, ERROR_MESSAGES } from '@/utils';

// Common validation schemas
const nameSchema = z
  .string()
  .min(VALIDATION.NAME_MIN_LENGTH, ERROR_MESSAGES.INVALID_NAME)
  .max(VALIDATION.NAME_MAX_LENGTH, ERROR_MESSAGES.INVALID_NAME);

const bpmnSchema = z
  .string()
  .min(1, ERROR_MESSAGES.REQUIRED_FIELD)
  .refine(
    (value) => value.includes('<?xml') && value.includes('bpmn:definitions'),
    ERROR_MESSAGES.INVALID_BPMN
  );

const scriptSchema = z
  .string()
  .max(VALIDATION.SCRIPT_MAX_LENGTH, ERROR_MESSAGES.SCRIPT_TOO_LONG);

// Process Definition Form Schema
export const processDefinitionSchema = z.object({
  name: nameSchema,
  bpmnXml: bpmnSchema,
});

export type ProcessDefinitionFormData = z.infer<typeof processDefinitionSchema>;

// Script Form Schema
export const scriptFormSchema = z.object({
  content: scriptSchema,
});

export type ScriptFormData = z.infer<typeof scriptFormSchema>;

// Process Variable Form Schema
export const processVariableSchema = z.object({
  name: z.string().min(1, ERROR_MESSAGES.REQUIRED_FIELD),
  value: z.string().min(1, ERROR_MESSAGES.REQUIRED_FIELD),
  type: z.enum(['string', 'number', 'boolean', 'object']),
  scope: z.string().optional(),
});

export type ProcessVariableFormData = z.infer<typeof processVariableSchema>;

// Generic form hook with validation
const useFormWithValidation = <
  TFieldValues extends FieldValues = FieldValues,
  TContext = unknown,
>(
  schema: z.ZodType<TFieldValues>,
  options?: Omit<UseFormProps<TFieldValues, TContext>, 'resolver'>
) => {
  return useForm<TFieldValues>({
    ...options,
    resolver: zodResolver(schema),
  });
};

// Specific form hooks
export const useProcessDefinitionForm = (
  options?: Omit<UseFormProps<ProcessDefinitionFormData>, 'resolver'>
) => {
  return useFormWithValidation(processDefinitionSchema, options);
};

export const useScriptForm = (
  options?: Omit<UseFormProps<ScriptFormData>, 'resolver'>
) => {
  return useFormWithValidation(scriptFormSchema, options);
};

export const useProcessVariableForm = (
  options?: Omit<UseFormProps<ProcessVariableFormData>, 'resolver'>
) => {
  return useFormWithValidation(processVariableSchema, options);
};

export default useFormWithValidation;
