/* Comportement de changement de langue. Le dictionnaire I18N est défini dans la coquille HTML. */
var UI_LANG = "fr";
function setUILang(lang) {
  if (!I18N[lang]) lang = "fr";
  UI_LANG = lang;
  var dict = I18N[lang] || {};
  var rtl = (lang === "ar" || lang === "he" || lang === "fa");
  document.documentElement.lang = lang;
  document.documentElement.dir = rtl ? "rtl" : "ltr";
  try { localStorage.setItem("unocr.uiLang", lang); } catch (e) {}
  document.querySelectorAll("[data-i18n]").forEach(function (el) {
    var value = dict[el.getAttribute("data-i18n")];
    if (value === undefined || value === null) return;
    el.textContent = Array.isArray(value) ? value[0] : value;
  });
  var title = document.getElementById("pageTitle");
  var subtitle = document.getElementById("pageSub");
  var active = document.querySelector(".nav-item[aria-current='true'], .nav-item.active");
  var key = active ? "page." + active.getAttribute("data-tab").replace("tab-", "") : null;
  if (title && key && dict[key]) title.textContent = dict[key][0];
  if (subtitle && key && dict[key]) subtitle.textContent = dict[key][1];
  var search = document.getElementById("globalSearch");
  if (search && dict["search.placeholder"]) search.placeholder = dict["search.placeholder"];
  document.querySelectorAll(".lang-btn").forEach(function (button) {
    button.setAttribute("aria-pressed", String(button.getAttribute("data-lang") === lang));
  });
  document.dispatchEvent(new CustomEvent("unocr:lang", { detail: { lang: lang, rtl: rtl } }));
}
document.querySelectorAll(".lang-btn").forEach(function (button) {
  button.addEventListener("click", function () { setUILang(button.getAttribute("data-lang")); });
});
try {
  var saved = localStorage.getItem("unocr.uiLang");
  if (saved && I18N[saved]) setUILang(saved);
} catch (e) {}
