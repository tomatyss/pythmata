import ServiceTaskPropertiesPanel from './ServiceTaskPropertiesPanel';

/**
 * A properties provider for service tasks.
 * 
 * Adds a custom tab to the properties panel for service tasks.
 */
function ServiceTaskPropertiesProvider(propertiesPanel, translate) {
  // Register our custom properties panel
  propertiesPanel.registerProvider(500, this);

  this.getTabs = function(element) {
    // Only show for service tasks
    if (element.type !== 'bpmn:ServiceTask') {
      return [];
    }

    return [
      {
        id: 'service-task',
        label: 'Service Task',
        component: ServiceTaskPropertiesPanel,
        isEdited: function() {
          return false;
        }
      }
    ];
  };
}

ServiceTaskPropertiesProvider.$inject = ['propertiesPanel', 'translate'];

export default ServiceTaskPropertiesProvider;
