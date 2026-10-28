// Words for /open, chosen by the email the link came from (?from=) and by
// any error Supabase put on the link. See open.html.
(function () {
  var app = window.SiddhaOpenApp;
  if (!app) return;
  var params = app.params;
  var from = params.get('from');
  var failed = !!params.get('error');
  var expired = failed && /expired|invalid/i.test((params.get('error_code') || '') + ' ' + (params.get('error_description') || ''));

  var TICK = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9.5" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="m7.8 12.4 2.8 2.8 5.6-5.8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  var ALERT = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9.5" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M12 7.2v6M12 16.6v.01" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';

  var copy;
  if (failed) {
    copy = {
      state: 'error', badge: ALERT,
      title: expired ? 'This link has expired' : 'This link didn’t work',
      body: 'Email links work once and only for an hour. Open Siddha and ask for a new one.',
    };
  } else if (from === 'confirm') {
    copy = { state: 'done', badge: TICK, title: 'Email confirmed', body: 'Your Siddha account is ready. Go back to the app to sign in and carry on.' };
  } else if (from === 'signin') {
    copy = { state: 'done', badge: TICK, title: 'One more tap', body: 'Open Siddha to finish signing in.' };
  } else if (from === 'reset') {
    copy = { state: 'done', badge: TICK, title: 'Choose a new password', body: 'Open Siddha to set your new password.' };
  } else if (from === 'email') {
    copy = { state: 'done', badge: TICK, title: 'Email change confirmed', body: 'Open Siddha to carry on.' };
  }

  var card = document.getElementById('card');
  if (copy) {
    card.setAttribute('data-state', copy.state);
    document.getElementById('badge').innerHTML = copy.badge;
    document.getElementById('title').textContent = copy.title;
    document.getElementById('body').textContent = copy.body;
    document.title = copy.title + ' · Siddha';
  }

  var getLink = document.getElementById('get-link');
  var getText = document.getElementById('get-text');
  getLink.href = app.storeUrl;
  if (app.platform === 'ios') {
    getText.textContent = 'Don’t have Siddha on this iPhone yet?';
    getLink.textContent = 'Get it from TestFlight';
  } else if (app.platform === 'android') {
    getText.textContent = 'Don’t have Siddha on this phone yet?';
    getLink.textContent = 'Get it on Google Play';
  } else {
    getText.textContent = 'Siddha is a phone app, for Android and iPhone.';
    getLink.textContent = 'See how to get it';
    getLink.href = '/#invite';
  }

  var showGet = function () {
    var get = document.getElementById('get');
    get.classList.add('is-forward');
    getText.textContent = 'Siddha didn’t open. If it isn’t on this phone yet:';
  };

  if (app.platform === 'desktop') {
    document.getElementById('desktop-note').hidden = false;
    return;
  }
  var main = document.getElementById('open-main');
  var top = document.getElementById('open-top');
  main.hidden = false;
  top.hidden = false;
  // Both carry the link's code, so whichever is tapped finishes the sign-in.
  app.bind(main, true, showGet);
  app.bind(top, true, showGet);
})();
