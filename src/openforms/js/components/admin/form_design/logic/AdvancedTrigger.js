import React, {useEffect, useState} from 'react';
import jsonLogic from 'json-logic-js';
import PropTypes from 'prop-types';
import {useIntl} from 'react-intl';
import classNames from 'classnames';

import {TextArea} from '../../forms/Inputs';
import DataPreview from './DataPreview';

const JsonWidget = ({name, logic, onChange}) => {
  const intl = useIntl();
  const [jsonError, setJsonError] = useState('');
  const [editorValue, setEditorValue] = useState(JSON.stringify(logic));

  useEffect(() => {
    setEditorValue(JSON.stringify(logic));
  }, [logic]);

  const invalidSyntaxMessage = intl.formatMessage({
    description: 'Advanced logic rule invalid json message',
    defaultMessage: 'Invalid JSON syntax',
  });
  const invalidLogicMessage = intl.formatMessage({
    description: 'Advanced logic rule invalid JSON-logic message',
    defaultMessage: 'Invalid JSON logic expression',
  });

  const onJsonChange = event => {
    const newValue = event.target.value;
    setEditorValue(newValue);
    setJsonError('');

    let updatedJson;

    try {
      updatedJson = JSON.parse(newValue);
    } catch (error) {
      if (error instanceof SyntaxError) {
        setJsonError(invalidSyntaxMessage);
        return;
      } else {
        throw error;
      }
    }

    if (!jsonLogic.is_logic(updatedJson)) {
      setJsonError(invalidLogicMessage);
      return;
    }

    const fakeEvent = {target: {name: name, value: updatedJson}};
    onChange(fakeEvent);
  };

  return (
    <div className="json-widget">
      <div className="json-widget__input">
        <TextArea name={name} value={editorValue} onChange={onJsonChange} cols={60} />
      </div>
      {jsonError.length ? <div className="json-widget__error">{jsonError}</div> : null}
    </div>
  );
};

JsonWidget.propTypes = {
  name: PropTypes.string.isRequired,
  logic: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
};

const AdvancedTrigger = ({name, logic, onChange, error}) => {
  return (
    <div className="logic-trigger">
      <div
        className={classNames('logic-trigger__json-editor', {
          'logic-trigger__json-editor--error': error,
        })}
      >
        <JsonWidget name={name} logic={logic} onChange={onChange} />
        {error ? <div className="logic-trigger__error">{error}</div> : null}
      </div>
      <div className="logic-trigger__data-preview">
        <DataPreview data={logic} />
      </div>
    </div>
  );
};

AdvancedTrigger.propTypes = {
  name: PropTypes.string.isRequired,
  logic: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  error: PropTypes.string,
};

export default AdvancedTrigger;
