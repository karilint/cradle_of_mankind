// https://www.w3schools.com/howto/howto_css_modals.asp

// Get the contact form modal
var contact_modal = document.getElementById("contact-form");

// Get the button that opens the contact form modal
var contact_btn = document.getElementById("contact-form-btn");

// Get the <span> element that closes the contact form modal
var contact_span = document.getElementById("contact-form-close");

// When the user clicks on the button, open the modal
contact_btn.onclick = function () {
  contact_modal.style.display = "block";
}

// When the user clicks on <span> (x), close the modal
contact_span.onclick = function () {
  contact_modal.style.display = "none";
}

// Get the logout modal
var logout_modal = document.getElementById("logout-modal");

// Get the button that opens the logout modal
var logout_btn = document.getElementById("logout-btn");

// Get the <span> element that closes the logout modal
var logout_span = document.getElementById("logout-close");

if (logout_btn != null) {
  // When the user clicks on the button, open the modal
  logout_btn.onclick = function () {
    logout_modal.style.display = "block";
  }

  // When the user clicks on <span> (x), close the modal
  logout_span.onclick = function () {
    logout_modal.style.display = "none";
  }
}

// Get the login modal
var login_modal = document.getElementById("login-modal");

// Get the button that opens the login modal
var login_btn = document.getElementById("login-btn");

// Get the <span> element that closes the login modal
var login_span = document.getElementById("login-close");

if (login_btn != null) {
  // When the user clicks on the button, open the modal
  login_btn.onclick = function () {
    login_modal.style.display = "block";
    console.log("hello")
  }

  // When the user clicks on <span> (x), close the modal
  login_span.onclick = function () {
    login_modal.style.display = "none";
  }
}

// When the user clicks anywhere outside of the modal, close it
window.onclick = function (event) {
  if (event.target == contact_modal) {
    contact_modal.style.display = "none";
  } else if (event.target == logout_modal) {
    logout_modal.style.display = "none";
  } else if (event.target == login_modal) {
    login_modal.style.display = "none";
  }
}
