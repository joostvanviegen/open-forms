import React, {useContext} from 'react';
import PropTypes from 'prop-types';

import Select from '../forms/Select';
import {FormContext} from './Context';

const getStepDisplayName = step => step.internalName || step.name;

const StepSelection = ({name, value, onChange}) => {
  const formContext = useContext(FormContext);
  const formSteps = formContext.formSteps;
  const formStepChoices = formSteps.map((step, index) => {
    const display = getStepDisplayName(step);
    const identifier = step.url || step._generatedId;
    return [identifier, display];
  });

  return (
    <Select name={name} choices={formStepChoices} allowBlank onChange={onChange} value={value} />
  );
};

StepSelection.propTypes = {
  name: PropTypes.string.isRequired,
  value: PropTypes.string,
  onChange: PropTypes.func,
};

/**
 * Look up the form step in the form context by identifier.
 *
 * @param  {String} identifier  The URL for persisted steps or generated ID for non-persisted steps.
 * @return {Object|null}        Object with the step instance from the context, or null if no identifier was provided.
 */
const useFormStep = (identifier = '') => {
  const formContext = useContext(FormContext);
  const formSteps = formContext.formSteps;
  if (!identifier) return null;

  // look up the step from the array of steps in the context
  const step = formSteps.find(element => {
    const urlMatch = element.url && element.url === identifier;
    const generatedIdMatch = element._generatedId === identifier;
    return urlMatch || generatedIdMatch;
  });
  return {
    step,
    stepName: getStepDisplayName(step),
  };
};

export default StepSelection;
export {useFormStep, StepSelection};
