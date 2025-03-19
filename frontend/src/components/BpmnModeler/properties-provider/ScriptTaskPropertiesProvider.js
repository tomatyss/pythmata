import ScriptTaskPropertiesPanel from './ScriptTaskPropertiesPanel';

/**
 * A properties provider for script tasks.
 * 
 * Adds a custom tab to the properties panel for script tasks.
 * 
 * @param {Object} propertiesPanel - The properties panel instance
 * @param {Function} translate - The translation function
 */
function ScriptTaskPropertiesProvider(propertiesPanel, translate) {
  // Register our custom properties panel
  propertiesPanel.registerProvider(500, this);

  this.getTabs = function(element) {
    // Only show for script tasks
    if (element.type !== 'bpmn:ScriptTask') {
      return [];
    }

    return [
      {
        id: 'script-task',
        label: 'Script',
        component: ScriptTaskPropertiesPanel,
        isEdited: function() {
          return false;
        }
      }
    ];
  };
}

ScriptTaskPropertiesProvider.$inject = ['propertiesPanel', 'translate'];

export default ScriptTaskPropertiesProvider;
