/// <reference types="vite/client" />

// Declare module types for packages that don't have TypeScript definitions
declare module 'bpmn-js/lib/Modeler' {
  export default class BpmnModeler {
    constructor(options: {
      container: HTMLElement;
      keyboard?: { bindTo: Document };
    });
    importXML(xml: string): Promise<{ warnings: Array<string> }>;
    saveXML(options?: { format?: boolean }): Promise<{ xml: string }>;
    destroy(): void;
  }
}

// Extend Window interface for any global variables
declare interface Window {
  // Add any custom window properties here
}

// Declare module for any static assets
declare module '*.svg' {
  const content: string;
  export default content;
}

declare module '*.png' {
  const content: string;
  export default content;
}

declare module '*.jpg' {
  const content: string;
  export default content;
}

declare module '*.json' {
  const content: Record<string, unknown>;
  export default content;
}

// Declare module for CSS modules
declare module '*.module.css' {
  const classes: { [key: string]: string };
  export default classes;
}

declare module '*.module.scss' {
  const classes: { [key: string]: string };
  export default classes;
}

// Declare module for any other file types you might use
declare module '*.bpmn' {
  const content: string;
  export default content;
}

// Add any other custom type declarations here
