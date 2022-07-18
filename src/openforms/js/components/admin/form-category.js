import jsonScriptToVar from '../../utils/json-script';
import {apiCall} from '../../utils/fetch';

const init = async () => {
  const nodes = document.querySelectorAll('.form-category.form-category--has-children');
  if (!nodes.length) return;
  // read the original GET params so we can include them in the async calls
  const GETParams = jsonScriptToVar('request-GET');

  const promises = Array.from(nodes).map(node => loadFormsForCategory(node, GETParams));
  await Promise.all(promises);

  // from admin/js/actions.js
  const actionsEls = document.querySelectorAll('tr input.action-select');
  if (actionsEls.length > 0) {
    window.Actions(actionsEls);
  }
};

const loadFormsForCategory = async (node, GETParams) => {
  // node is a table row, after which we have to inject the forms.
  const {id, depth: _depth} = node.dataset;
  const loader = node.parentNode.querySelector('.form-category__loader');
  const depth = parseInt(_depth);
  const query = {
    ...GETParams,
    _async: 1,
    category: id,
  };

  node.addEventListener('click', event => {
    event.preventDefault();
    node.classList.toggle('form-category--collapsed');

    // check the siblings and extract the rows that are children of the current node
    let tableBody = node.parentNode.nextElementSibling;

    // loop over all next table bodies and check the form category rows for their depth.
    // as soon as the depth value falls below our own depth value, we are done collapsing
    // child nodes.
    while (tableBody) {
      const categoryRow = tableBody.querySelector('.form-category');
      if (parseInt(categoryRow.dataset.depth) <= depth) {
        break;
      }
      categoryRow.classList.toggle('form-category--hidden');
      categoryRow.classList.add('form-category--collapsed');
      tableBody = tableBody.nextElementSibling;
    }
  });

  // TODO: handle pagination
  const response = await apiCall(`.?${new URLSearchParams(query)}`);
  // handle pagination
  const pageNumbers = response.headers
    .get('X-Pagination-Pages')
    .split(',')
    .map(p => parseInt(p));
  const extraPageNumbers = pageNumbers.slice(1); // we already fetched the first page just now

  // set up extra requests for the additional pages
  const promises = extraPageNumbers.map(async page => {
    const pageQuery = new URLSearchParams({...query, p: page});
    const response = await apiCall(`.?${pageQuery}`);
    return await response.text();
  });

  const htmlBlobs = [await response.text(), ...(await Promise.all(promises))];

  // create a dom element in memory to render the table, and then take out only what's
  // relevant
  const fragment = document.createDocumentFragment();
  for (const htmlBlob of htmlBlobs) {
    const container = document.createElement('div');
    container.insertAdjacentHTML('afterbegin', htmlBlobs[0]);
    const rows = container.querySelectorAll('tbody tr');
    for (const row of rows) {
      row.dataset['depth'] = depth;
      row.dataset['category'] = id;
      row.classList.add('form-category__item');
      fragment.appendChild(row);
    }
  }
  loader && node.parentNode.removeChild(loader);
  node.after(fragment);
};

if (document.readyState !== 'loading') {
  init();
} else {
  document.addEventListener('DOMContentLoaded', init);
}
