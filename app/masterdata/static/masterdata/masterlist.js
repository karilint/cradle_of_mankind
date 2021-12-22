const searchField = document.getElementById("search")
const filterButton = document.getElementById("filter-button")
const clearButton = document.getElementById("clear-button")
const clearButton2 = document.getElementById("clear-button2")

clearButton.onclick = () => {
  searchField.value = ""
  filterButton.click()
}

clearButton2.onclick = () => {
  searchField.value = ""
  filterButton.click()
}

hide_show = () => {
  const x = document.getElementById("hide_show");
  if (x.style.display === "none") {
    x.style.display = "block";
  } else {
    x.style.display = "none";
  }
}
