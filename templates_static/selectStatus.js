
function selectCurrentStatus(status) {
  var select = document.getElementById('status-query');
  for (i = 0; i < select.options.length; i++) {
    if (select.options[i] == status) {
      select.selectedIndex = i
      break
    }
  }
}