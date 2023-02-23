// Burger menus
document.addEventListener('DOMContentLoaded', function() {
    // open
    const burger = document.querySelectorAll('.navbar-burger');
    const menu = document.querySelectorAll('.navbar-menu');

    if (burger.length && menu.length) {
        for (var i = 0; i < burger.length; i++) {
            burger[i].addEventListener('click', function() {
                for (var j = 0; j < menu.length; j++) {
                    menu[j].classList.toggle('hidden');
                }
            });
        }
    }

    // close
    const close = document.querySelectorAll('.navbar-close');
    const backdrop = document.querySelectorAll('.navbar-backdrop');

    if (close.length) {
        for (var i = 0; i < close.length; i++) {
            close[i].addEventListener('click', function() {
                for (var j = 0; j < menu.length; j++) {
                    menu[j].classList.toggle('hidden');
                }
            });
        }
    }

    if (backdrop.length) {
        for (var i = 0; i < backdrop.length; i++) {
            backdrop[i].addEventListener('click', function() {
                for (var j = 0; j < menu.length; j++) {
                    menu[j].classList.toggle('hidden');
                }
            });
        }
    }
});
function setActiveNav() {
  var currentPage = window.location.href.split('/').pop(); // extract page name from URL
  var navLinks = document.querySelectorAll('.nav-link');

  for (var i = 0; i < navLinks.length; i++) {
    var link = navLinks[i];
    var linkPage = link.getAttribute('id').split('-')[0]; // extract page name from link ID
    var linkPage2 = link.getAttribute('id').split('-')[1];
    if ("" === currentPage && linkPage == "home") {
        link.classList.remove('text-gray-300');
        link.classList.remove('hover:bg-gray-800');
        link.classList.add('bg-blue-500');
        link.classList.add('text-white');

    }else{
        if (linkPage === currentPage || linkPage2+'s' === currentPage) {
          link.classList.remove('text-gray-300');
          link.classList.remove('hover:bg-gray-800');
          link.classList.add('bg-blue-500');
          link.classList.add('text-white');

        } else {
          link.classList.remove('text-white');
          link.classList.remove('bg-blue-500');
          link.classList.add('hover:bg-gray-800');
          link.classList.add('text-gray-300');
        }
    }
  }
}
window.onload = function() {
  setActiveNav();
};