import ElementPropertiesProvider from './ElementPropertiesProvider';
import ScriptTaskPropertiesProvider from './ScriptTaskPropertiesProvider';

export default {
  __init__: ['propertiesProvider', 'scriptTaskPropertiesProvider'],
  propertiesProvider: ['type', ElementPropertiesProvider],
  scriptTaskPropertiesProvider: ['type', ScriptTaskPropertiesProvider]
};
