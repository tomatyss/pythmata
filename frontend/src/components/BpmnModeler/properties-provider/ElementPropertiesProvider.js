import ElementPropertiesPanel from './ElementPropertiesPanel';

/**
 * A properties provider for all BPMN elements.
 * 
 * Adds a custom tab to the properties panel for all BPMN elements.
 * 
 * @param {Object} propertiesPanel - The properties panel instance
 * @param {Function} translate - The translation function
 */
function ElementPropertiesProvider(propertiesPanel, translate) {
  // Register our custom properties panel
  propertiesPanel.registerProvider(500, this);

  this.getTabs = function(element) {
    // Show for all elements
    return [
      {
        id: 'element-properties',
        label: 'Properties',
        component: ElementPropertiesPanel,
        isEdited: function() {
          return false;
        }
      }
    ];
  };
}

ElementPropertiesProvider.$inject = ['propertiesPanel', 'translate'];

export default ElementPropertiesProvider;
