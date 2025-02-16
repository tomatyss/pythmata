declare module 'bpmn-js' {
  export interface Canvas {
    zoom(type: 'fit-viewport'): void;
  }

  export interface Overlays {
    add(
      elementId: string,
      options: {
        position: {
          top: number;
          left: number;
        };
        html: string;
      }
    ): void;
    clear(): void;
  }

  export interface ModdleElement {
    id: string;
    type: string;
    businessObject?: {
      name?: string;
      documentation?: string;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  }

  export interface ElementRegistry {
    get(id: string): ModdleElement | undefined;
    getAll(): ModdleElement[];
  }

  export interface ImportXMLResult {
    warnings: Array<Error>;
  }

  export default class BpmnJS {
    constructor(options?: { container?: HTMLElement });

    importXML(xml: string): Promise<ImportXMLResult>;
    destroy(): void;

    get(service: 'canvas'): Canvas;
    get(service: 'overlays'): Overlays;
    get(service: 'elementRegistry'): ElementRegistry;
    get(service: string): unknown;
  }
}
