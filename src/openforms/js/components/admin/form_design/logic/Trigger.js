import React, {useContext} from 'react';
import PropTypes from 'prop-types';
import {useIntl, FormattedMessage} from 'react-intl';
import {useImmerReducer} from 'use-immer';
import jsonLogic from 'json-logic-js';

import {getTranslatedChoices} from '../../../../utils/i18n';
import ArrayInput from '../../forms/ArrayInput';
import ComponentSelection from '../../forms/ComponentSelection';
import Select from '../../forms/Select';

import {OPERATORS, COMPONENT_TYPE_TO_OPERATORS, COMPONENT_TYPE_TO_OPERAND_TYPE} from './constants';
import LiteralValueInput from './LiteralValueInput';
import OperandTypeSelection from './OperandTypeSelection';
import DataPreview from './DataPreview';
import DSLEditorNode from './DSLEditorNode';
import {useOnChanged} from './hooks';
import Today from './Today';
import {FormContext} from '../Context';

const OperatorSelection = ({name, selectedComponent, operator, onChange}) => {
  const intl = useIntl();
  // check the component type, which is used to filter the possible choices
  const formContext = useContext(FormContext);
  const allComponents = formContext.components;
  const componentType = allComponents[selectedComponent]?.type;

  // only keep the relevant choices
  const allowedOperators =
    COMPONENT_TYPE_TO_OPERATORS[componentType] || COMPONENT_TYPE_TO_OPERATORS._default;
  const choices = Object.entries(OPERATORS).filter(([operator]) =>
    allowedOperators.includes(operator)
  );
  if (!choices.length) {
    return null;
  }

  return (
    <Select
      name={name}
      choices={getTranslatedChoices(intl, choices)}
      allowBlank
      onChange={onChange}
      value={operator}
    />
  );
};

OperatorSelection.propTypes = {
  name: PropTypes.string.isRequired,
  selectedComponent: PropTypes.string.isRequired,
  operator: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
};

const initialState = {
  component: '',
  operator: '',
  operandType: '',
  operand: '',
};

const TRIGGER_FIELD_ORDER = ['component', 'operator', 'operandType', 'operand'];

const parseJsonLogic = (logic, allComponents) => {
  // Algorithm mostly taken from https://github.com/jwadhams/json-logic-js/blob/master/logic.js, combined
  // with our own organization.
  if (!logic || !Object.keys(logic).length) return {};

  // reference for parsing: https://jsonlogic.com/
  // a rule is always in the format {"operator": ["values" ...]} -> so grab the operator
  const operator = jsonLogic.get_operator(logic);
  let values = logic[operator];
  if (!Array.isArray(values)) {
    values = [values];
  }

  // first value should be the reference to the component
  let component = values[0].date ? values[0].date.var : values[0].var;
  if (Array.isArray(component)) {
    // Case where a default is defined
    component = component[0];
  }

  // check if we're using a literal value, or a component reference
  let compareValue = values[1];
  let operandType = '';
  let operand = '';

  // Selectboxes case: the component name contains the reference to which value, e.g. "selectComponentField.option1"
  if (!allComponents[component]) {
    let componentBits = component.split('.');
    component = componentBits.slice(0, componentBits.length - 1).join('.');
    compareValue = componentBits.slice(componentBits.length - 1).join('.');
  }

  if (jsonLogic.is_logic(compareValue)) {
    const op = jsonLogic.get_operator(compareValue);
    switch (op) {
      case 'var': {
        operandType = 'component';
        operand = compareValue.var;
        break;
      }
      case 'date': {
        operandType = compareValue.date.var ? 'component' : 'literal';
        operand = compareValue.date.var ? compareValue.date.var : compareValue.date;
        break;
      }
      case '+':
      case '-': {
        operandType = 'today';
        operand = compareValue;
        break;
      }
      default:
        console.warn(`Unsupported operator: ${op}, can't derive operandType`);
    }
  } else if (compareValue != null) {
    if (Array.isArray(compareValue)) {
      operandType = 'array';
    } else {
      operandType = 'literal';
    }
    operand = compareValue;
  }

  return {
    component,
    operator,
    operandType,
    operand,
  };
};

const reducer = (draft, action) => {
  switch (action.type) {
    case 'TRIGGER_CONFIGURATION_CHANGED': {
      const {name, value} = action.payload;
      draft[name] = value;

      // clear the dependent fields if needed - e.g. if the component changes, all fields to the right change
      const currentFieldIndex = TRIGGER_FIELD_ORDER.indexOf(name);
      const nextFieldNames = TRIGGER_FIELD_ORDER.slice(currentFieldIndex + 1);
      for (const name of nextFieldNames) {
        draft[name] = initialState[name];
      }
      break;
    }
    default: {
      throw new Error(`Unknown action type: ${action.type}`);
    }
  }
};

const Trigger = ({name, logic, onChange, error, withDSLPreview = false, children}) => {
  const formContext = useContext(FormContext);
  const allComponents = formContext.components;
  // break down the json logic back into variables that can be managed by components state
  const parsedLogic = parseJsonLogic(logic, allComponents);
  const [state, dispatch] = useImmerReducer(reducer, {...initialState, ...parsedLogic});

  // event handlers
  const onTriggerChange = event => {
    const {name, value} = event.target;
    dispatch({
      type: 'TRIGGER_CONFIGURATION_CHANGED',
      payload: {
        name,
        value,
      },
    });
  };

  // rendering logic
  const {component: triggerComponent, operator, operandType, operand} = state;

  const componentType = allComponents[triggerComponent]?.type;

  let compareValue = null;
  let valueInput = null;

  switch (operandType) {
    case 'literal': {
      valueInput = (
        <LiteralValueInput
          name="operand"
          componentType={componentType}
          value={operand.toString()}
          onChange={onTriggerChange}
        />
      );
      if (componentType === 'date') {
        compareValue = {date: operand};
      } else {
        compareValue = operand;
      }
      break;
    }
    case 'component': {
      valueInput = (
        <ComponentSelection
          name="operand"
          value={operand}
          onChange={onTriggerChange}
          // filter components of the same type as the trigger component
          filter={comp => comp.type === componentType}
        />
      );
      if (componentType === 'date') {
        compareValue = {date: {var: operand}};
      } else {
        compareValue = {var: operand};
      }
      break;
    }
    case 'today': {
      valueInput = <Today name="operand" onChange={onTriggerChange} value={operand} />;

      let sign, relativeDelta;
      if (operand) {
        sign = jsonLogic.get_operator(operand);
        relativeDelta = operand[sign][1].rdelta || [0, 0, 0];
      } else {
        sign = '+';
        relativeDelta = [0, 0, 0];
      }
      compareValue = {};
      compareValue[sign] = [{today: []}, {rdelta: relativeDelta}];
      break;
    }
    case 'array': {
      valueInput = (
        <ArrayInput
          name="operand"
          inputType="text"
          values={operand}
          onChange={value => {
            const fakeEvent = {target: {name: 'operand', value: value}};
            onTriggerChange(fakeEvent);
          }}
        />
      );
      compareValue = operand;
      break;
    }
    case '': {
      // nothing selected yet
      break;
    }
    default: {
      throw new Error(`Unknown operand type: ${operandType}`);
    }
  }

  let firstOperand;
  switch (componentType) {
    case 'date': {
      firstOperand = {date: {var: triggerComponent}};
      break;
    }
    case 'selectboxes': {
      firstOperand = {var: `${triggerComponent}.${compareValue}`};
      compareValue = true;
      break;
    }
    case 'checkbox': {
      firstOperand = {var: triggerComponent};
      // cast from string to actual boolean
      if (compareValue === 'true') compareValue = true;
      if (compareValue === 'false') compareValue = false;
      break;
    }
    default:
      firstOperand = {var: triggerComponent};
  }

  const jsonLogicFromState = {
    [operator]: [firstOperand, compareValue],
  };

  // whenever we get a change in the jsonLogic definition, relay that back to the
  // parent component
  useOnChanged(jsonLogicFromState, () => onChange({target: {name, value: jsonLogicFromState}}));

  return (
    <div className="logic-trigger">
      <div className="logic-trigger__editor">
        {error && <div className="logic-trigger__error">{error}</div>}
        <div className="dsl-editor">
          <DSLEditorNode errors={null}>
            <FormattedMessage description="Logic trigger prefix" defaultMessage="When" />
          </DSLEditorNode>
          <DSLEditorNode errors={null}>
            <ComponentSelection
              name="component"
              value={triggerComponent}
              onChange={onTriggerChange}
            />
          </DSLEditorNode>
          {triggerComponent ? (
            <DSLEditorNode errors={null}>
              <OperatorSelection
                name="operator"
                selectedComponent={triggerComponent}
                operator={operator}
                onChange={onTriggerChange}
              />
            </DSLEditorNode>
          ) : null}
          {triggerComponent && operator ? (
            <DSLEditorNode errors={null}>
              <OperandTypeSelection
                name="operandType"
                operandType={operandType}
                onChange={onTriggerChange}
                filter={([choiceKey, choiceLabel]) => {
                  if (!componentType) return true;
                  return getOperandTypesForComponentType(componentType).includes(choiceKey);
                }}
              />
            </DSLEditorNode>
          ) : null}
          {triggerComponent && operator && operandType ? (
            <DSLEditorNode errors={null}>{valueInput}</DSLEditorNode>
          ) : null}
        </div>
      </div>

      {children ? <div className="logic-trigger__children">{children}</div> : null}

      {withDSLPreview && (
        <div className="logic-trigger__data-preview">
          <DataPreview data={jsonLogicFromState} />
        </div>
      )}
    </div>
  );
};

Trigger.propTypes = {
  name: PropTypes.string.isRequired,
  logic: PropTypes.object,
  onChange: PropTypes.func.isRequired,
  error: PropTypes.string,
  withDSLPreview: PropTypes.bool,
  children: PropTypes.node,
};

const getOperandTypesForComponentType = componentType => {
  const types =
    COMPONENT_TYPE_TO_OPERAND_TYPE[componentType] || COMPONENT_TYPE_TO_OPERAND_TYPE._default;
  return types;
};

export default Trigger;
