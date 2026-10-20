// asksiddha.app/buy: sign in with the app's Supabase account, then pay with
// Razorpay. The server (/api/v1/store/web/*, astrospace/api/web_store_routes.py)
// checks every payment with Razorpay before the plan turns on; this page only
// opens checkout and shows the result.
//
// Sign-in uses Supabase's redirect flow without its JS client: Google or an
// email link comes back to /buy with the session in the URL fragment, which
// is read once, kept in sessionStorage for this tab, and wiped from the URL.
(function () {
  'use strict';
  var API = '/api/v1/store/web';
  var TOKEN_KEY = 'siddha.buy.token';
  var EXPIRY_KEY = 'siddha.buy.expires';
  var WANT_KEY = 'siddha.buy.want';
  var TIER_RANK = { plus: 1, pro: 2 };
  var TIER_NAME = { plus: 'Plus', pro: 'Practitioner' };
  var PLAN_POINTS = {
    plus: ['5 questions a month in Ask', 'Daily, weekly and monthly readings', 'Full remedy plan, Muhurta and compatibility', 'Charts for 3 people'],
    pro: ['Everything in Plus', '15 questions a month in Ask', 'All divisional charts and Practitioner mode', 'Charts for up to 10 people']
  };

  var cfg = null;
  var me = null;
  var busy = false;

  function $(id) { return document.getElementById(id); }
  function show(id, on) { $(id).hidden = !on; }
  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    for (var key in attrs || {}) node.setAttribute(key, attrs[key]);
    if (text != null) node.textContent = text;
    return node;
  }
  function store(key, value) {
    try {
      if (value == null) sessionStorage.removeItem(key); else sessionStorage.setItem(key, value);
    } catch (e) { /* private mode: the session lasts for this page view only */ }
  }
  function load(key) {
    try { return sessionStorage.getItem(key); } catch (e) { return null; }
  }
  var memoryToken = null;

  function notice(text, tone) {
    var node = $('notice');
    node.textContent = text || '';
    node.setAttribute('data-tone', tone || 'info');
    node.hidden = !text;
    if (text) node.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
  function rupees(n) { return '₹' + Number(n).toLocaleString('en-IN'); }
  function day(iso) {
    if (!iso) return '';
    var d = new Date(/Z|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + 'Z');
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
  }

  // --- Session ---------------------------------------------------------------

  function takeSessionFromUrl() {
    if (!location.hash || location.hash.length < 2) return;
    var params = new URLSearchParams(location.hash.slice(1));
    var token = params.get('access_token');
    var error = params.get('error_description');
    if (token) {
      var seconds = parseInt(params.get('expires_in') || '3600', 10);
      memoryToken = token;
      store(TOKEN_KEY, token);
      store(EXPIRY_KEY, String(Date.now() + (seconds - 60) * 1000));
    } else if (error) {
      notice('Sign-in did not finish: ' + error.replace(/\+/g, ' ') + '. Please try again.', 'bad');
    }
    if (token || error) history.replaceState(null, '', location.pathname + location.search);
  }

  function token() {
    var saved = load(TOKEN_KEY) || memoryToken;
    var expires = parseInt(load(EXPIRY_KEY) || '0', 10);
    if (saved && (!expires || expires > Date.now())) return saved;
    return null;
  }

  function signOut() {
    memoryToken = null;
    store(TOKEN_KEY, null);
    store(EXPIRY_KEY, null);
    me = null;
    render();
  }

  function returnUrl() { return location.origin + '/buy'; }

  function signInWithGoogle() {
    location.href = cfg.supabase_url + '/auth/v1/authorize?provider=google&redirect_to=' +
      encodeURIComponent(returnUrl());
  }

  function emailLink(event) {
    event.preventDefault();
    var email = $('email').value.trim();
    if (!email) return;
    fetch(cfg.supabase_url + '/auth/v1/otp?redirect_to=' + encodeURIComponent(returnUrl()), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', apikey: cfg.supabase_anon_key },
      // Only existing accounts: the plan has to land where the app will find it.
      body: JSON.stringify({ email: email, create_user: false })
    }).then(function (response) {
      if (response.ok) {
        notice('Check your inbox for a sign-in link from Siddha. Open it on this device.', 'good');
      } else if (response.status === 422 || response.status === 400) {
        notice('There is no Siddha account with that email. Sign up in the app first, then come back.', 'bad');
      } else if (response.status === 429) {
        notice('Too many sign-in emails just now. Wait a minute and try again.', 'bad');
      } else {
        notice('The sign-in email could not be sent. Please try again.', 'bad');
      }
    }, function () { notice('No connection. Please try again.', 'bad'); });
  }

  // --- Server ---------------------------------------------------------------

  function api(path, body) {
    return fetch(API + path, {
      method: body ? 'POST' : 'GET',
      headers: Object.assign({ Authorization: 'Bearer ' + token() }, body ? { 'Content-Type': 'application/json' } : {}),
      body: body ? JSON.stringify(body) : undefined
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (data) {
        if (response.status === 401) { signOut(); throw new Error('Please sign in again.'); }
        if (!response.ok) throw new Error(data.detail || 'Something went wrong. Please try again.');
        return data;
      });
    });
  }

  function refresh() {
    if (!token()) { render(); return Promise.resolve(); }
    return api('/me').then(function (data) { me = data; render(); resumeWanted(); },
      function (error) { notice(error.message, 'bad'); render(); });
  }

  // --- Checkout -------------------------------------------------------------

  var checkoutScript = null;
  function loadCheckout() {
    if (window.Razorpay) return Promise.resolve();
    if (!checkoutScript) {
      checkoutScript = new Promise(function (resolve, reject) {
        var script = el('script', { src: 'https://checkout.razorpay.com/v1/checkout.js' });
        script.onload = resolve;
        script.onerror = function () { checkoutScript = null; reject(new Error('The payment window could not load. Check your connection and try again.')); };
        document.head.appendChild(script);
      });
    }
    return checkoutScript;
  }

  function buy(product) {
    if (busy) return;
    if (!me) {
      // Signed out: remember the choice and start checkout after sign-in.
      store(WANT_KEY, product.id);
      notice('Sign in first, so the purchase lands on your Siddha account.', 'info');
      $('signin').scrollIntoView({ block: 'center', behavior: 'smooth' });
      return;
    }
    busy = true;
    notice('');
    render();
    Promise.all([api('/checkout', { product_id: product.id }), loadCheckout()]).then(function (results) {
      var order = results[0];
      var options = {
        key: order.key_id,
        name: 'Siddha',
        description: order.product.title,
        image: location.origin + '/img/icon-192.png',
        prefill: { email: order.email || '' },
        theme: { color: '#b13f2e' },
        handler: function (paid) {
          notice('Payment received. Turning it on…', 'info');
          api('/confirm', paid).then(function (data) {
            me = data;
            busy = false;
            notice(product.kind === 'plan'
              ? 'Done. ' + TIER_NAME[product.tier] + ' is on. Open the Siddha app to use it.'
              : 'Done. ' + product.questions + (product.questions === 1 ? ' question was' : ' questions were') + ' added to your account.', 'good');
            render();
          }, function () {
            busy = false;
            notice('Your payment went through. It can take a minute to show here and in the app; refresh shortly.', 'info');
            setTimeout(refresh, 8000);
            render();
          });
        },
        modal: { ondismiss: function () { busy = false; render(); } }
      };
      if (order.subscription_id) options.subscription_id = order.subscription_id;
      else { options.order_id = order.order_id; options.amount = order.amount; options.currency = order.currency; }
      var checkout = new window.Razorpay(options);
      checkout.on('payment.failed', function (response) {
        var reason = response && response.error && response.error.description;
        notice('The payment did not go through' + (reason ? ': ' + reason : '') + '. You have not been charged.', 'bad');
      });
      checkout.open();
    }).catch(function (error) {
      busy = false;
      notice(error.message, 'bad');
      render();
    });
  }

  function cancel(plan) {
    var ends = day(plan.renews_at || plan.expires_at);
    if (!window.confirm('Stop renewing ' + TIER_NAME[plan.tier] + '? It stays on until ' + ends + ', and you will not be charged again.')) return;
    busy = true;
    render();
    api('/cancel', { subscription_id: plan.subscription_id }).then(function (data) {
      me = data;
      busy = false;
      notice(TIER_NAME[plan.tier] + ' will not renew. It stays on until ' + day(plan.expires_at) + '.', 'good');
      render();
    }, function (error) { busy = false; notice(error.message, 'bad'); render(); });
  }

  // Someone who tapped "Get Plus" on the landing page and then signed in
  // lands back here with the choice remembered; start that checkout once.
  function resumeWanted() {
    var want = load(WANT_KEY);
    if (!want || !me || !me.may_buy) return;
    store(WANT_KEY, null);
    var product = (cfg.products || []).filter(function (p) { return p.id === want; })[0];
    if (product && !owned(product)) buy(product);
  }

  function owned(product) {
    return product.kind === 'plan' && me && me.paid_tier_rank >= TIER_RANK[product.tier];
  }

  // --- Render ---------------------------------------------------------------

  function renderStatus() {
    var box = $('status');
    box.textContent = '';
    var line = function (text) { var p = el('p', { 'class': 'row' }); p.appendChild(el('span', { 'class': 'muted' }, text)); box.appendChild(p); return p; };
    if (!me) return;
    var web = me.web_plans || [];
    web.forEach(function (plan) {
      var row = line(plan.renews_at
        ? TIER_NAME[plan.tier] + ', bought here. Renews on ' + day(plan.renews_at) + '.'
        : TIER_NAME[plan.tier] + ', bought here. Ends on ' + day(plan.expires_at) + ' and will not renew.');
      if (plan.renews_at) {
        var stop = el('button', { 'class': 'btn link', type: 'button' }, 'Stop renewing');
        stop.disabled = busy;
        stop.addEventListener('click', function () { cancel(plan); });
        row.appendChild(stop);
      }
    });
    (me.store_plans || []).forEach(function (plan) {
      line(TIER_NAME[plan.tier] + ' through Google Play or the App Store. Manage or cancel it there.');
    });
    if (!web.length && !(me.store_plans || []).length) {
      line(me.access_tier === 'free' ? 'You are on Free.' : 'Your account has ' + (TIER_NAME[me.access_tier] || me.access_tier) + ' access.');
    }
    if (me.question_credits) line('Extra questions on your account: ' + me.question_credits + '.');
    if (!me.may_buy) line('Buying on the website is open to a few testers for now.');
  }

  function planCard(product) {
    var card = el('article', { 'class': 'glass plan' + (product.tier === 'plus' ? ' featured' : '') });
    card.appendChild(el('h2', {}, 'Siddha ' + TIER_NAME[product.tier]));
    var price = el('p', { 'class': 'price' }, rupees(product.price_inr) + ' ');
    price.appendChild(el('small', {}, 'a month'));
    card.appendChild(price);
    var list = el('ul');
    (PLAN_POINTS[product.tier] || []).forEach(function (point) { list.appendChild(el('li', {}, point)); });
    card.appendChild(list);
    var have = owned(product);
    var button = el('button', { 'class': 'btn' + (product.tier === 'plus' ? ' primary' : ''), type: 'button' },
      have ? 'You have this' : 'Get ' + TIER_NAME[product.tier]);
    button.disabled = busy || have || (me && !me.may_buy);
    button.addEventListener('click', function () { buy(product); });
    card.appendChild(button);
    return card;
  }

  function render() {
    show('loading', false);
    var open = cfg && cfg.enabled;
    show('closed', !open);
    show('testmode', open && cfg.test_mode);
    var signedIn = open && !!token();
    show('signin', open && !signedIn);
    show('account', signedIn && !!me);
    show('shop', open);
    if (!open) return;

    $('who-email').textContent = (me && me.email) || '';
    renderStatus();

    var plans = $('plans');
    plans.textContent = '';
    var packs = $('packs');
    packs.textContent = '';
    (cfg.products || []).forEach(function (product) {
      if (product.kind === 'plan') {
        plans.appendChild(planCard(product));
      } else {
        var label = (product.questions === 1 ? '1 question' : product.questions + ' questions') + ' · ' + rupees(product.price_inr);
        var button = el('button', { 'class': 'btn', type: 'button' }, label);
        button.disabled = busy || (me && !me.may_buy);
        button.addEventListener('click', function () { buy(product); });
        packs.appendChild(button);
      }
    });
    show('packs-panel', packs.childNodes.length > 0);
  }

  // --- Start ----------------------------------------------------------------

  takeSessionFromUrl();
  var wanted = new URLSearchParams(location.search).get('plan');
  if (wanted) store(WANT_KEY, wanted === 'practitioner' ? 'siddha_practitioner_monthly' : wanted === 'plus' ? 'siddha_plus_monthly' : null);

  $('google').addEventListener('click', function () { signInWithGoogle(); });
  $('email-form').addEventListener('submit', emailLink);
  $('signout').addEventListener('click', signOut);

  fetch(API + '/config').then(function (r) { return r.ok ? r.json() : { enabled: false }; }, function () { return { enabled: false }; })
    .then(function (data) { cfg = data; render(); return refresh(); });
})();
