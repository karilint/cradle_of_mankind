
function chooseEmptyOptions() {
  var selects = document.getElementsByClassName("master_field_selects");
  for (i = 0; i < selects.length; i++) {
    var select = selects[i];
    for (j = 0; j < select.options.length; j++) {
      if (select.options[j].text == "Empty") {
        select.selectedIndex = j;
        break;
      }
    }
  }
}

chooseEmptyOptions()

