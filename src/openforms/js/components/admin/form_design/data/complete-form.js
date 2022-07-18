import produce from 'immer';

import {ValidationErrors} from '../../../../utils/exception';
import {post, put, apiDelete} from '../../../../utils/fetch';
import {FORM_ENDPOINT} from '../constants';
import {saveLogicRules, savePriceRules} from './logic';
import {updateOrCreateFormSteps} from './steps';
import {createOrUpdateFormVariables} from './variables';
import {createFormVersion} from './versions';

const getStepsByGeneratedId = formSteps => {
  const stepsWithGeneratedId = formSteps.filter(step => !!step._generatedId);
  return Object.fromEntries(stepsWithGeneratedId.map(step => [step._generatedId, step]));
};

/**
 * Resolve temporary step IDs to actual URLs.
 *
 * This requires the stepsByGeneratedId being up-to-date with server-side UUID/URLs,
 * so typically you can only call this after all the form steps are committed to the
 * backend.
 *
 * This relies on the client-side _generatedId still being around while the URL has been
 * set. If the passed in stepIdentifier is a URL, it is left untouched. If not, it is
 * assumed to be a generated ID and the step is looked up in the `stepsByGeneratedId`
 * mapping.
 *
 * The return value is the URL reference (if applicable).
 */
const getStepReference = (stepsByGeneratedId, stepIdentifier, stepAttribute = 'url') => {
  // empty-ish value -> leave untouched
  if (!stepIdentifier) return stepIdentifier;
  try {
    new URL(stepIdentifier);
    // if it's a URL, return it - this was already set by the backend.
    return stepIdentifier;
  } catch {
    const step = stepsByGeneratedId[stepIdentifier];
    return step[stepAttribute];
  }
};

/**
 * Save the form itself without any related objects.
 */
const saveForm = async (state, csrftoken) => {
  const {
    newForm: isNewForm,
    form: {uuid},
  } = state;
  const formDetails = produce(state, draft => {
    return {
      ...draft.form,
      literals: draft.literals,
      authenticationBackends: draft.selectedAuthPlugins,
    };
  });

  const createOrUpdate = isNewForm ? post : put;
  const endpoint = isNewForm ? FORM_ENDPOINT : `${FORM_ENDPOINT}/${uuid}`;

  // throws on HTTP 400, HTTP 401 or any non-OK status.
  let response;
  try {
    response = await createOrUpdate(endpoint, csrftoken, formDetails, true);
  } catch (e) {
    // wrap validation errors so the component knows where to display the errors
    if (e instanceof ValidationErrors) {
      e.context = 'form';
      throw e;
    }
    // unknown, re-throw
    throw e;
  }

  // update with the backend generated data, like UUID and URL. Note that this is a noop
  // for form updates.
  const newState = produce(state, draft => {
    const {uuid, url, literals} = response.data;
    draft.form.uuid = uuid;
    draft.form.url = url;
    draft.literals = literals;
    draft.newForm = false; // it's either created now, or updated -> both are not 'new form anymore'
  });
  return newState;
};

/**
 * Save the form steps and their related form definitions + report back any
 * validation errors.
 */
const saveSteps = async (state, csrftoken) => {
  const createdFormDefinitions = [];

  const {
    form: {url: formUrl},
    formSteps,
    stepsToDelete,
  } = state;

  const results = await updateOrCreateFormSteps(csrftoken, formUrl, formSteps, formDefinition =>
    createdFormDefinitions.push(formDefinition)
  );

  let validationErrors = [];
  // store the URL references once persisted in the backend
  let newState = produce(state, draft => {
    // add any newly created form definitions to the state
    for (const formDefinition of createdFormDefinitions) {
      draft.formDefinitions.push(formDefinition);
    }
    // process the FormStep results (success or error)
    for (const result of results) {
      // set the step validation errors in the state if it was not a success
      if (result instanceof ValidationErrors) {
        validationErrors.push(result);
        continue;
      }
      const {index, uuid, url, formDefinition} = result;
      draft.formSteps[index].uuid = uuid;
      draft.formSteps[index].url = url;
      draft.formSteps[index].formDefinition = formDefinition;
    }
  });

  const hasErrors = !!validationErrors.length;
  if (!hasErrors) {
    // delete the steps marked for deletion
    // TODO: error handling in case this fails - the situation before refactor
    // was also a bit dire, the internal state was never cleaned up.
    await Promise.all(stepsToDelete.map(async step => await apiDelete(step, csrftoken)));
    newState = produce(newState, draft => {
      draft.stepsToDelete = [];
    });
  }

  return [newState, validationErrors];
};

/**
 * Save the logic rules and price rules, report back any validation errors.
 */
const saveLogic = async (state, csrftoken) => {
  const {
    form: {url: formUrl},
  } = state;

  const stepsByGeneratedId = getStepsByGeneratedId(state.formSteps);

  let newState = produce(state, draft => {
    for (const rule of draft.logicRules) {
      // fix the trigger from step reference
      rule.triggerFromStep = getStepReference(stepsByGeneratedId, rule.triggerFromStep);
      // fix the actions that do something with the step(s)
      for (const action of rule.actions) {
        action.formStep = getStepReference(stepsByGeneratedId, action.formStep);
      }
    }
  });

  // form logic
  const {logicRules, logicRulesToDelete, priceRules, priceRulesToDelete} = newState;

  const logicResults = await saveLogicRules(formUrl, csrftoken, logicRules, logicRulesToDelete);
  const priceResults = await savePriceRules(formUrl, csrftoken, priceRules, priceRulesToDelete);

  // update the state with updated references
  const validationErrors = [];
  newState = produce(state, draft => {
    for (const [index, result] of logicResults.entries()) {
      if (result instanceof ValidationErrors) {
        validationErrors.push(result);
        continue;
      }

      const {url, uuid} = result;
      draft.logicRules[index].uuid = uuid;
      draft.logicRules[index].url = url;
    }

    for (const [index, result] of priceResults.entries()) {
      if (result instanceof ValidationErrors) {
        validationErrors.push(result);
        continue;
      }

      const {url, uuid} = result;
      draft.priceRules[index].uuid = uuid;
      draft.priceRules[index].url = url;
    }

    draft.logicRulesToDelete = [];
    draft.priceRulesToDelete = [];
  });

  return [newState, validationErrors];
};

/**
 * Save the variables belonging to the form, user defined and derived from
 * the form steps.
 */
const saveVariables = async (state, csrftoken) => {
  const {
    form: {url: formUrl},
  } = state;

  const stepsByGeneratedId = getStepsByGeneratedId(state.formSteps);
  let newState = produce(state, draft => {
    for (const variable of draft.formVariables) {
      variable.form = formUrl;
      variable.formDefinition = getStepReference(
        stepsByGeneratedId,
        variable.formDefinition,
        'formDefinition'
      );
    }
  });

  // make the actual API call
  let errors = [];
  try {
    const response = await createOrUpdateFormVariables(formUrl, newState.formVariables, csrftoken);
    // update the state with server-side objects
    newState = produce(newState, draft => {
      draft.formVariables = response.data;
    });
  } catch (e) {
    if (e instanceof ValidationErrors) {
      e.context = 'variables';
      // TODO: convert in list of errors for further processing?
      errors = [e];
    } else {
      // re-throw any other type of error
      throw e;
    }
  }

  return [newState, errors];
};

const saveVersion = async (state, csrftoken) => {
  await createFormVersion(state.form.url, csrftoken);
};

/**
 * Save the complete form, including all the steps, logic,...
 *
 * Note that this function is tightly coupled with the FormCreationForm component state.
 *
 * We use the immer produce function to 'commit' state changes that happen during saving
 * into the next immutable object so that following steps can use the expected data
 * structures where temporary IDs etc. have been resolved.
 *
 * TODO: refactor out csrftoken argument everywhere.
 *
 * @param  {String} csrftoken CSRF-Token from backend
 * @param  {Object} state     The FormCreationForm state at the moment of submission
 * @return {Object}           Updated state with resolved temporary IDs
 */
const saveCompleteForm = async (state, featureFlags, csrftoken) => {
  // various save actions for parts of the form result in (gradual) state updates. At
  // the end, we will have a new component state that we can just set/dispatch. This
  // allows us to update internal references when their persistent identifiers have been
  // created in the backend.
  //
  // We leverage immer's produce function for this and to ensure we work with immutable
  // data-structures.
  let newState;
  let logicValidationErrors = [];
  let stepsValidationErrors = [];
  let variableValidationErrors = [];

  // first, persist the form itself as everything is related to this. If this succeeds
  // without validation errors, then `newState.form.uuid` will be set, guaranteed.
  try {
    newState = await saveForm(state, csrftoken);
  } catch (e) {
    if (e instanceof ValidationErrors) {
      return [state, [e]];
    }
    throw e;
  }

  // then, ensure the form definitions and steps are persisted
  [newState, stepsValidationErrors] = await saveSteps(newState, csrftoken);
  if (stepsValidationErrors.length) {
    // if there are errors in the steps, we cannot continue with logic/variables etc.
    // before the steps are properly committed to the DB
    return [newState, stepsValidationErrors];
  }

  // save (normal) logic and price logic rules
  [newState, logicValidationErrors] = await saveLogic(newState, csrftoken);

  // variables - only if feature flag is enabled!
  if (featureFlags.enable_form_variables) {
    [newState, variableValidationErrors] = await saveVariables(newState, csrftoken);
  }

  const validationErrors = [...logicValidationErrors, ...variableValidationErrors];
  if (!validationErrors.length) {
    // Save this new version of the form in the "form version control"
    await saveVersion(newState, csrftoken);
  }
  return [newState, validationErrors];
};

export {saveCompleteForm};
