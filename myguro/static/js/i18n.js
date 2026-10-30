// Text in the language the person chose, for every page's JavaScript (loaded by base.html, so the pages that do
// not load common.js, like the login page, have it too).

// t("{count} to do", { count: 3 }) -> "3 pa ang gagawin" in Taglish, "3 to do" in English. The English sentence is
// the key; window.TEXT holds the Taglish (empty in English), and a sentence with no entry stays English.
function t(text, values = {}) {
  const found = (window.TEXT && window.TEXT[text]) || text;
  return found.replace(/\{(\w+)\}/g, (match, name) => (name in values ? String(values[name]) : match));
}
