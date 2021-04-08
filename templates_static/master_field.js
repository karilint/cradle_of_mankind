
function fillFieldsWithCurrentValues(name, desc) {
  var name_field = document.getElementById('id_field_name');
  var desc_field = document.getElementById('id_field_description');
  name_field.value = name
  desc_field.value = desc
}

fillFieldsWithCurrentValues(master_field_name, master_field_desc)
