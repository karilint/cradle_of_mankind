function select_current_display_order(master_fields) {
  console.log(typeof master_fields)
  console.log(master_fields)
  for (master_field in master_fields.keys) {
    var select = document.getElementById(master_field.name)
    console.log(1)
    console.log(master_field)
  }
}

select_current_display_order(current_display_orders)

