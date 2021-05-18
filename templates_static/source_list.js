
function selectCurrentSource(source_id) {
  var select = document.getElementById('source-query');
  if (source_id == 'all') {
    select.selectedIndex = 0;
  } else {
    for (i = 0; i < select.options.length; i++) {
      if (select.options[i].value == source_id) {
        select.selectedIndex = i
        break
      }
    }
  }
}

selectCurrentSource(current_source_id)
