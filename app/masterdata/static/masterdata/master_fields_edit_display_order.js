const saveButtons = document.getElementsByClassName('requires-changes');
const orderingForm = document.getElementById('orderingForm');
const formInput = orderingForm.querySelector('#orderingInput');
function saveOrdering() {
  const rows = document.getElementById('master-fields').querySelectorAll('tr');
  let ids = [];
  for (let row of rows) {
    ids.push(row.dataset.id);
  }
  formInput.value = ids.join(',');
  orderingForm.submit();
}
Array.from(saveButtons).forEach((button) => {
  button.addEventListener('click', saveOrdering);
});

const rows = document.getElementById('master-fields');
let sortable = Sortable.create(rows, {
  animation: 150,
  handle: '.handle',
  dragClass: 'dragged',
  chosenClass: 'sortableChosen',
  onChange: () => {
    Array.from(saveButtons).forEach((button) => {
      button.disabled = false;
      button.title = '';
      button.classList.remove('requires-changes');
    });
  },
});

