document.querySelectorAll(".row").forEach(row => {
  const track = row.querySelector(".track");
  const scroll = dir => track.scrollBy({ left: dir * track.clientWidth * 0.85 });
  row.querySelector(".l").onclick = () => scroll(-1);
  row.querySelector(".r").onclick = () => scroll(1);
});

const nav = document.querySelector(".nav");
addEventListener("scroll", () => nav.classList.toggle("solid", scrollY > 40), { passive: true });

const q = document.getElementById("q");
const box = document.getElementById("results");
let timer;

q.addEventListener("input", () => {
  clearTimeout(timer);
  const v = q.value.trim();
  if (v.length < 2) return (box.innerHTML = "");
  timer = setTimeout(async () => {
    const res = await fetch(`/search/?json=1&q=${encodeURIComponent(v)}`);
    const { results } = await res.json();
    box.innerHTML = results
      .map(r => `<a href="${r.url}">${r.title} <small>${r.kind}${r.year ? " · " + r.year : ""}</small></a>`)
      .join("") || "<p>No results</p>";
  }, 250);
});