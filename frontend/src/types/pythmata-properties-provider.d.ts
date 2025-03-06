declare module '@/components/BpmnModeler/properties-provider' {
  // Define a more specific type for the properties provider module
  const ServiceTaskPropertiesProviderModule: {
    __init__: string[];
    __depends__?: unknown[];
    propertiesProvider: unknown[];
  };
  export default ServiceTaskPropertiesProviderModule;
}
