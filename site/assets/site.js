// Small behaviours shared by every page: old one-page links, the gallery filters,
// the before-and-after wipe, the contact address, and the phone menu.
(() => {
  // links to the old single page (index.html#bolted_joint, #tasks, ...) go to the page that now holds them
  const legacy = window.LEGACY;
  if (legacy) {
    const key = decodeURIComponent(location.hash.slice(1));
    if (key && legacy[key]) { location.replace(legacy[key]); return; }
  }

  // gallery: filter by discipline
  const cards = [...document.querySelectorAll("#gallery .wcard")];
  const btns = [...document.querySelectorAll(".filters button")];
  btns.forEach(b => b.addEventListener("click", () => {
    btns.forEach(x => x.setAttribute("aria-pressed", x === b ? "true" : "false"));
    const f = b.dataset.f;
    cards.forEach(c => { c.hidden = !(f === "all" || c.dataset.group === f); });
  }));

  // before-and-after wipes
  document.querySelectorAll(".wipe").forEach(w => {
    const r = w.querySelector(".wipe-range");
    r.addEventListener("input", () => w.style.setProperty("--pos", r.value + "%"));
  });

  // contact: the address is stored reversed and base64-encoded, and decoded only when someone asks for it
  const mail = document.getElementById("contact-mail"), show = document.getElementById("contact-show"), out = document.getElementById("contact-addr");
  if (mail) {
    const addr = () => atob(mail.dataset.m).split("").reverse().join("");
    const subject = encodeURIComponent("Simulation work");
    mail.addEventListener("click", e => { e.preventDefault(); location.href = `mailto:${addr()}?subject=${subject}`; });
    show.addEventListener("click", () => {
      const a = document.createElement("a");
      a.href = `mailto:${addr()}?subject=${subject}`; a.textContent = addr();
      out.replaceChildren(a); out.hidden = false; show.hidden = true;
    });
  }

  // phone menu: close when a link is chosen or the page is clicked elsewhere
  const menu = document.querySelector(".menu");
  if (menu) document.addEventListener("click", e => { if (menu.open && !e.target.closest(".menu > summary")) menu.open = false; });
})();
