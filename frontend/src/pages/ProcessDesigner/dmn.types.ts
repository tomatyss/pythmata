// DMN-specific types
export interface DmnElement {
    id: string;
    type: string;
    businessObject: DmnBusinessObject;
}
  
export interface DmnBusinessObject {
    id: string;
    name?: string;
}
  
export interface DmnElementRegistry {
    get(id: string): DmnElement;
    find(filter: (element: DmnElement) => boolean): DmnElement[];
    filter(filter: (element: DmnElement) => boolean): DmnElement[];
    forEach(callback: (element: DmnElement) => void): void;
}
  
export interface DmnModeling {
    updateProperties(
      element: DmnElement,
      properties: Record<string, unknown>
    ): void;
}

export interface Moddle {
    create<T>(type: string, properties?: Record<string, unknown>): T;
  }

export interface EventBus {
    on<T = unknown>(event: string, callback: (event: T) => void): void;
}

export interface DmnModuleTypeMap {
    elementRegistry: DmnElementRegistry;
    modeling: DmnModeling;
    eventBus: EventBus;
    moddle: Moddle;
}
  
export type DmnModelerModule = keyof DmnModuleTypeMap;
  
export type ExtendedDmnModeler = import('dmn-js/lib/Modeler').default & {
    get<T extends DmnModelerModule>(name: T): DmnModuleTypeMap[T];
};
  
export interface DmnModelerOptions {
    container: HTMLElement;
    drd?: {
      additionalModules?: unknown[];
    };
    decisionTable?: {
      additionalModules?: unknown[];
    };
    literalExpression?: {
      additionalModules?: unknown[];
    };
}