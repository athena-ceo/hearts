// <h-card c="SQ"> draws a card.  Add "small" for the small size and "button" for a card you can choose.
const SUIT = { C: "♣", D: "♦", H: "♥", S: "♠" };
const NAME = { C: "clubs", D: "diamonds", H: "hearts", S: "spades" };
const RANK = { A: "ace", K: "king", Q: "queen", J: "jack" };
customElements.define("h-card", class extends HTMLElement {
  connectedCallback() {
    const code = this.getAttribute("c"), suit = code[0], rank = code.slice(1);
    const tag = this.hasAttribute("button") ? "button" : "span";
    const face = document.createElement(tag);
    face.className = "card" + (suit === "H" || suit === "D" ? " red" : "") + (this.hasAttribute("small") ? " small" : "");
    if (tag === "button") { face.type = "button"; face.setAttribute("aria-pressed", "false"); }
    face.setAttribute("aria-label", `${RANK[rank] || rank} of ${NAME[suit]}`);
    if (tag === "span") face.setAttribute("role", "img");
    for (const [name, text] of [["rank", rank], ["pip", SUIT[suit]], ["big", SUIT[suit]]]) {
      const part = document.createElement("span");
      part.className = name; part.textContent = text; part.setAttribute("aria-hidden", "true");
      face.append(part);
    }
    this.append(face);
  }
});
