// Define types for BPMN elements and properties
export interface BusinessObject {
  id: string;
  scriptFormat?: string;
  resultVariable?: string;
  extensionElements?: {
    values: ExtensionElement[];
  };
}

export interface BpmnElement {
  id: string;
  type: string;
  businessObject: BusinessObject;
}

// Define types for extension elements
export interface ExtensionElement {
  $type: string;
  taskName?: string;
  timeout?: string;
  properties?: {
    values: PropertyValue[];
  };
}

export interface PropertyValue {
  name: string;
  value: string;
}

// Define types for the modeler modules
export interface ElementRegistry {
  get(id: string): BpmnElement;
  find(filter: (element: BpmnElement) => boolean): BpmnElement[];
  filter(filter: (element: BpmnElement) => boolean): BpmnElement[];
  forEach(callback: (element: BpmnElement) => void): void;
}

export interface Modeling {
  updateProperties(
    element: BpmnElement,
    properties: Record<string, unknown>
  ): void;
}

export interface Moddle {
  create<T>(type: string, properties?: Record<string, unknown>): T;
}

export interface EventBus {
  on<T = unknown>(event: string, callback: (event: T) => void): void;
}

// Define a mapping of module names to their types
export interface ModuleTypeMap {
  elementRegistry: ElementRegistry;
  modeling: Modeling;
  moddle: Moddle;
  eventBus: EventBus;
}

// Define a type for the modeler with the methods we need
export type ModelerModule = keyof ModuleTypeMap;

// BpmnModeler type with our extensions
export type ExtendedBpmnModeler = import('bpmn-js/lib/Modeler').default & {
  get<T extends ModelerModule>(name: T): ModuleTypeMap[T];
};

// Define a type for BpmnModeler options
export interface BpmnModelerOptions {
  container: HTMLElement;
  moddleExtensions?: Record<string, unknown>;
  palette?: {
    open: boolean;
  };
  keyboard?: {
    bindTo: Document;
  };
}
