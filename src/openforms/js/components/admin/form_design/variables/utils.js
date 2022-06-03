import _ from 'lodash';
import {Utils as FormioUtils} from 'formiojs';

import {COMPONENT_DATATYPES, VARIABLE_SOURCES} from './constants';

const getComponentDatatype = component => {
  if (component.multiple) {
    return [];
  }
  return COMPONENT_DATATYPES[component.type] || 'string';
};

const updateFormVariables = (
  formDefinition,
  mutationType,
  newComponent,
  oldComponent,
  currentFormVariables
) => {
  // Not all components are associated with variables
  if (FormioUtils.isLayoutComponent(newComponent)) return currentFormVariables;

  let updatedFormVariables = _.cloneDeep(currentFormVariables);
  const existingKeys = updatedFormVariables
    .filter(variable => variable.source === VARIABLE_SOURCES.component)
    .map(variable => variable.key);

  // The 'change' event is emitted for both create and update events
  if (mutationType === 'changed') {
    // This is either a create event, or the key of the component has changed
    if (!existingKeys.includes(newComponent.key)) {
      // The URL of the form will be added during the onSubmit callback (so that the formUrl is available)
      updatedFormVariables.push({
        name: newComponent.label,
        key: newComponent.key,
        formDefinition: formDefinition,
        source: VARIABLE_SOURCES.component,
        isSensitiveData: newComponent.isSensitiveData,
        prefillPlugin: newComponent.prefill?.plugin || '',
        prefillAttribute: newComponent.prefill?.attribute || '',
        dataType: getComponentDatatype(newComponent),
        initialValue: newComponent.defaultValue || '',
      });

      // This is the case where the key of a component has been changed
      if (newComponent.key !== oldComponent.key) {
        updatedFormVariables = updatedFormVariables.filter(
          variable => variable.key !== oldComponent.key
        );
      }
    } else {
      // This is the case where other attributes (not the key) of the component have changed.
      updatedFormVariables = updatedFormVariables.map(variable => {
        if (variable.key !== newComponent.key) return variable;

        return {
          ...variable,
          name: newComponent.label,
          prefillPlugin: newComponent.prefill?.plugin || '',
          prefillAttribute: newComponent.prefill?.attribute || '',
          isSensitiveData: newComponent.isSensitiveData,
          initialValue: newComponent.defaultValue || '',
        };
      });
    }
  } else if (mutationType === 'removed') {
    // When a component is removed, oldComponent is null
    updatedFormVariables = updatedFormVariables.filter(
      variable => variable.key !== newComponent.key
    );
  }

  return updatedFormVariables;
};

export {updateFormVariables};
