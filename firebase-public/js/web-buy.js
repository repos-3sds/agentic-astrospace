// Shows the "Get Plus on the web" links once the server says website checkout
// is open (Razorpay keys set). Until then, and if this call fails, the page
// reads exactly as before.
(function () {
  fetch('/api/v1/store/web/config').then(function (r) { return r.ok ? r.json() : null; }).then(function (cfg) {
    if (!cfg || !cfg.enabled) return;
    var links = document.querySelectorAll('[data-web-buy]');
    for (var i = 0; i < links.length; i++) links[i].hidden = false;
  }, function () {});
})();
