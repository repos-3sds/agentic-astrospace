// Shows plan prices in rupees for visitors in India and in US dollars
// everywhere else, matching the Google Play prices. India is read from the
// browser's time zone, so there is no location prompt and no network call.
// The language setting is ignored: an Indian living abroad pays Play's
// dollar price there. The page ships with rupees, so it
// still reads correctly if this script never runs.
(function () {
  var zone = '';
  try { zone = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (e) {}
  if (zone === 'Asia/Kolkata' || zone === 'Asia/Calcutta') return;
  var nodes = document.querySelectorAll('[data-usd]');
  for (var i = 0; i < nodes.length; i++) nodes[i].textContent = nodes[i].getAttribute('data-usd');
})();
