/**
 * Retrieves the root element from the DOM.
 * Throws an error if the root element is not found.
 * @returns {HTMLElement} The root element.
 */
export const getRootElement = (): HTMLElement => {
  const rootElement = document.getElementById('root');
  if (!rootElement) {
    throw new Error('Root element not found');
  }
  return rootElement;
};
