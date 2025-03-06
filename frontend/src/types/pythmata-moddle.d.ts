declare module '@/components/BpmnModeler/moddle/pythmata.json' {
  // Define a more specific type for the moddle descriptor
  const pythmataModdleDescriptor: {
    name: string;
    uri: string;
    prefix: string;
    types: Record<string, unknown>;
  };
  export default pythmataModdleDescriptor;
}
