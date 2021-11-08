const TEMPLATE = `
<div id="{{ctx.groupId}}" class="accordion builder-sidebar{{ctx.scrollEnabled ? ' builder-sidebar_scroll' : ''}}" ref="sidebar">
  <input class="form-control builder-sidebar_search" type="search" ref="sidebar-search" placeholder="{{ctx.t('Search field(s)')}}" />
  <div ref="sidebar-groups">
    {% ctx.groups.forEach(function(group) { %}
      {{ group }}
    {% }) %}
  </div>
</div>
`;

export default TEMPLATE;
