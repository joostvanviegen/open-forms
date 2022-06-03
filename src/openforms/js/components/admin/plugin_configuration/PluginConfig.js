import React from 'react';
import PropTypes from 'prop-types';
import {FormattedMessage} from 'react-intl';

import {Checkbox} from '../forms/Inputs';

const PluginConfig = ({module, plugin, label, enabled = true, onChange}) => {
  return (
    <>
      <Checkbox
        name={`plugin_configuration.${module}.${plugin}.enabled`}
        label={
          <FormattedMessage
            description="Plugin enabled label"
            defaultMessage="Enable {plugin}"
            values={{plugin: label}}
          />
        }
        checked={enabled}
        onChange={() => onChange(!enabled)}
      />
    </>
  );
};

PluginConfig.propTypes = {
  module: PropTypes.string.isRequired,
  plugin: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  enabled: PropTypes.bool,
  onChange: PropTypes.func,
};

export default PluginConfig;
