// "Open Siddha" from a web page: the button on /open (where sign-in emails
// land) and the "Open app" pill on the landing page.
//
// Both go through the app's custom scheme, which the app already handles
// (AuthService.handleNativeAuthCallback). On Android it is wrapped in an
// intent: URL, so Chrome falls back to the Play listing by itself when the
// app is missing. iOS has no such fallback, so if the page is still showing
// a moment after the tap, the "get the app" links are brought forward.
//
// Only the few parameters the app needs are carried across. Tokens are never
// forwarded: sign-in uses PKCE, so a link carries a one-time code that only
// the phone that asked for it can redeem.
(function () {
  var SCHEME = 'app.asksiddha.mobile';
  var PACKAGE = 'app.asksiddha.mobile';
  var PLAY = 'https://play.google.com/store/apps/details?id=app.asksiddha.mobile';
  var TESTFLIGHT = 'https://testflight.apple.com/join/tRHuKd21';
  var FORWARD = ['from', 'code', 'error', 'error_code', 'error_description'];

  var ua = navigator.userAgent || '';
  var ios = /iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1);
  var android = /Android/.test(ua);
  var platform = ios ? 'ios' : android ? 'android' : 'desktop';
  document.documentElement.setAttribute('data-platform', platform);

  // Supabase puts errors in the fragment and the code in the query.
  var params = new URLSearchParams(location.search);
  new URLSearchParams(location.hash.replace(/^#/, '')).forEach(function (value, key) {
    if (!params.has(key)) params.set(key, value);
  });

  function appLink(withParams) {
    var query = new URLSearchParams();
    if (withParams) FORWARD.forEach(function (key) { if (params.get(key)) query.set(key, params.get(key)); });
    var path = 'auth/callback' + (String(query) ? '?' + query : '');
    if (android) {
      return 'intent://' + path + '#Intent;scheme=' + SCHEME + ';package=' + PACKAGE +
        ';S.browser_fallback_url=' + encodeURIComponent(PLAY) + ';end';
    }
    return SCHEME + '://' + path;
  }

  function open(event, withParams, onMissing) {
    if (platform === 'desktop') return; // the link's own href explains
    event.preventDefault();
    var left = false;
    var onHide = function () { if (document.hidden) left = true; };
    document.addEventListener('visibilitychange', onHide);
    window.location.href = appLink(withParams);
    if (ios) {
      setTimeout(function () {
        document.removeEventListener('visibilitychange', onHide);
        if (!left && !document.hidden) onMissing();
      }, 1600);
    }
  }

  window.SiddhaOpenApp = {
    platform: platform,
    params: params,
    storeUrl: ios ? TESTFLIGHT : PLAY,
    bind: function (el, withParams, onMissing) {
      if (!el) return;
      el.addEventListener('click', function (event) { open(event, withParams, onMissing || function () {}); });
    },
  };
})();
