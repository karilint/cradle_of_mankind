function showHideTextField(question) {
  var div = document.getElementById(`add-field-${question}`);
  if (div.style.display == "flex") {
    div.style.display = "none"
    div.getElementsByTagName("input")[0].value = ""
  } else {
    div.style.display = "flex";
  }
}

function addOption(question) {
  var div = document.getElementById(`add-field-${question}`);
  var select = document.getElementById(question);
  var answer = div.getElementsByTagName("input")[0].value
  select.options[select.options.length] = new Option((answer, answer));
  select.selectedIndex = select.options.length - 1;
  div.style.display = "none"
}

function selectCurrentStatus(status) {
  var select = document.getElementById('status-query');
  for (i = 0; i < select.options.length; i++) {
    if (select.options[i] == status) {
      select.selectedIndex = i
      break
    }
  }
}