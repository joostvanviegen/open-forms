import React from 'react';

const FormDefinitionsContext = React.createContext([]);
FormDefinitionsContext.displayName = 'FormDefinitionsContext';

const FormStepsContext = React.createContext([]);
FormStepsContext.displayName = 'FormStepsContext';

const PluginsContext = React.createContext({
  availableAuthPlugins: [],
  selectedAuthPlugins: [],
  availablePrefillPlugins: [],
});
PluginsContext.displayName = 'PluginsContext';

const TinyMceContext = React.createContext('');
TinyMceContext.displayName = 'TinyMceContext';

const FormContext = React.createContext({url: ''});
FormContext.displayName = 'FormContext';

const FeatureFlagsContext = React.createContext({});
FeatureFlagsContext.displayName = 'FeatureFlagsContext';

export {
  FormContext,
  FormDefinitionsContext,
  FormStepsContext,
  PluginsContext,
  TinyMceContext,
  FeatureFlagsContext,
};
