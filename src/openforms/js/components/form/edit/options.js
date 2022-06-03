const LABEL = {
  type: 'textfield',
  key: 'label',
  label: 'Label',
};

const KEY = {
  type: 'textfield',
  key: 'key',
  label: 'Property Name',
  validate: {
    required: true,
  },
};

const DESCRIPTION = {
  type: 'textfield',
  key: 'description',
  label: 'Description',
};

const SHOW_IN_SUMMARY = {
  type: 'checkbox',
  key: 'showInSummary',
  label: 'Show in summary',
  tooltip: 'Whether to show this value in the submission summary',
  defaultValue: true,
};

const SHOW_IN_EMAIL = {
  type: 'checkbox',
  key: 'showInEmail',
  label: 'Show in email',
  tooltip: 'Whether to show this value in the confirmation email',
};

const SHOW_IN_PDF = {
  type: 'checkbox',
  key: 'showInPDF',
  label: 'Show in PDF',
  tooltip: 'Whether to show this value in the confirmation PDF',
  defaultValue: true,
};

const PRESENTATION = {
  type: 'panel',
  title: 'Display in summaries and confirmations',
  key: 'presentationConfig',
  components: [SHOW_IN_SUMMARY, SHOW_IN_EMAIL, SHOW_IN_PDF],
};

const MULTIPLE = {
  type: 'checkbox',
  key: 'multiple',
  label: 'Multiple values',
  tooltip: 'Are there multiple values possible for this field?',
};

const HIDDEN = {
  type: 'checkbox',
  key: 'hidden',
  label: 'Hidden',
  tooltip: 'Hide a field from the form.',
};

const CLEAR_ON_HIDE = {
  type: 'checkbox',
  key: 'clearOnHide',
  label: 'Clear on hide',
  tooltip:
    'Remove the value of this field from the submission if it is hidden. Note: the value of this field is then also not used in logic rules!',
};

const IS_SENSITIVE_DATA = {
  type: 'checkbox',
  key: 'isSensitiveData',
  label: 'Is Sensitive Data',
  tooltip:
    'The data entered in this component will be removed in accordance with the privacy settings.',
};

const DEFAULT_VALUE = {
  label: 'Default Value',
  key: 'defaultValue',
  tooltip: 'This will be the initial value for this field, before user interaction.',
  input: true,
};

const READ_ONLY = {
  // This doesn't work as in native HTML forms. Marking a field as 'disabled' only makes it read-only in the
  // UI, but the data is still sent to the backend.
  type: 'checkbox',
  label: 'Read only',
  tooltip: 'Make this component read only',
  key: 'disabled',
  input: true,
};

const REGEX_VALIDATION = {
  weight: 130,
  key: 'validate.pattern',
  label: 'Regular Expression Pattern',
  placeholder: 'Regular Expression Pattern',
  type: 'textfield',
  tooltip:
    'The regular expression pattern test that the field value must pass before the form can be submitted.',
  input: true,
};

export {
  LABEL,
  KEY,
  DESCRIPTION,
  SHOW_IN_SUMMARY,
  SHOW_IN_EMAIL,
  SHOW_IN_PDF,
  PRESENTATION,
  MULTIPLE,
  HIDDEN,
  CLEAR_ON_HIDE,
  IS_SENSITIVE_DATA,
  DEFAULT_VALUE,
  READ_ONLY,
  REGEX_VALIDATION,
};
