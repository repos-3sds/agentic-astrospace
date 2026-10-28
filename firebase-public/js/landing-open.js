// On a phone, the landing page's top-right button opens the app instead of
// asking for an invite (testers arrive here from emails and shared links).
// On iOS, if Siddha is not installed, /open explains how to get it.
(function () {
  var app = window.SiddhaOpenApp;
  var pill = document.querySelector('[data-open-app]');
  if (!app || !pill || app.platform === 'desktop') return;
  pill.hidden = false;
  var invite = document.querySelector('[data-invite-pill]');
  if (invite) invite.hidden = true;
  app.bind(pill, false, function () { window.location.href = '/open'; });
})();
