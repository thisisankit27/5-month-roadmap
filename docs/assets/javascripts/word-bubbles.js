(function () {
  "use strict";

  const DATA_URL = "assets/data/word-frequencies.json";
  // Tune these independently to control how dense the kinetic cloud feels.
  const MAX_BUBBLES_DESKTOP = 50;
  const MAX_BUBBLES_MOBILE = 17;
  const MOBILE_BREAKPOINT = "(max-width: 44.9375em)";

  function startKineticLayout(container, nodes) {
    const core = document.createElement("span");
    core.className = "word-map__gravity";
    core.textContent = "AI";
    core.setAttribute("aria-hidden", "true");
    container.appendChild(core);

    let width = 0;
    let height = 0;
    let centerX = 0;
    let centerY = 0;
    const coreRadius = 24;

    function measure() {
      const bounds = container.getBoundingClientRect();
      width = bounds.width;
      height = bounds.height;
      centerX = width / 2;
      centerY = height / 2;
      core.style.transform = `translate3d(${centerX - coreRadius}px, ${centerY - coreRadius}px, 0)`;
      nodes.forEach((node, index) => {
        if (!node.positioned) {
          const angle = index * 2.399963229728653;
          const distance = coreRadius + node.radius + 18 + Math.sqrt(index) * 31;
          node.x = centerX + Math.cos(angle) * distance;
          node.y = centerY + Math.sin(angle) * distance;
          node.positioned = true;
        }
        node.x = Math.max(node.radius, Math.min(width - node.radius, node.x));
        node.y = Math.max(node.radius, Math.min(height - node.radius, node.y));
      });
    }

    function excite(node) {
      let dx = node.x - centerX;
      let dy = node.y - centerY;
      let distance = Math.hypot(dx, dy) || 1;
      if (distance === 1) { dx = 1; dy = 0; }
      node.vx += (dx / distance) * 13;
      node.vy += (dy / distance) * 13;
      core.classList.remove("word-map__gravity--active");
      void core.offsetWidth;
      core.classList.add("word-map__gravity--active");
    }

    nodes.forEach((node) => {
      node.element.addEventListener("click", () => excite(node));
      node.element.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          excite(node);
        }
      });
    });

    function step() {
      if (!container.isConnected) return;
      for (const node of nodes) {
        const dx = centerX - node.x;
        const dy = centerY - node.y;
        node.vx += dx * 0.00075;
        node.vy += dy * 0.00075;

        const coreDx = node.x - centerX;
        const coreDy = node.y - centerY;
        const coreDistance = Math.hypot(coreDx, coreDy) || 1;
        const coreGap = coreRadius + node.radius + 10;
        if (coreDistance < coreGap) {
          const push = (coreGap - coreDistance) / coreDistance;
          node.x += coreDx * push;
          node.y += coreDy * push;
        }
      }

      for (let i = 0; i < nodes.length; i += 1) {
        for (let j = i + 1; j < nodes.length; j += 1) {
          const first = nodes[i];
          const second = nodes[j];
          let dx = second.x - first.x;
          let dy = second.y - first.y;
          let distance = Math.hypot(dx, dy) || 0.01;
          const minimumDistance = first.radius + second.radius + 5;
          if (distance >= minimumDistance) continue;
          dx /= distance;
          dy /= distance;
          const overlap = (minimumDistance - distance) / 2;
          first.x -= dx * overlap;
          first.y -= dy * overlap;
          second.x += dx * overlap;
          second.y += dy * overlap;
          const relativeVelocity = (second.vx - first.vx) * dx + (second.vy - first.vy) * dy;
          if (relativeVelocity < 0) {
            const impulse = relativeVelocity * 0.62;
            first.vx += impulse * dx;
            first.vy += impulse * dy;
            second.vx -= impulse * dx;
            second.vy -= impulse * dy;
          }
        }
      }

      for (const node of nodes) {
        node.vx *= 0.985;
        node.vy *= 0.985;
        node.x += node.vx;
        node.y += node.vy;
        if (node.x < node.radius || node.x > width - node.radius) node.vx *= -0.55;
        if (node.y < node.radius || node.y > height - node.radius) node.vy *= -0.55;
        node.x = Math.max(node.radius, Math.min(width - node.radius, node.x));
        node.y = Math.max(node.radius, Math.min(height - node.radius, node.y));
        node.element.style.transform = `translate3d(${node.x - node.radius}px, ${node.y - node.radius}px, 0)`;
      }
      requestAnimationFrame(step);
    }

    new ResizeObserver(measure).observe(container);
    measure();
    requestAnimationFrame(step);
  }

  function renderWordMap() {
    const map = document.querySelector("[data-word-map]");
    if (!map || map.dataset.loaded === "true") return;
    const summary = map.querySelector("[data-word-map-summary]");
    const bubbles = map.querySelector("[data-word-map-bubbles]");

    fetch(DATA_URL)
      .then((response) => {
        if (!response.ok) throw new Error("Word statistics data was not found.");
        return response.json();
      })
      .then((data) => {
        const bubbleLimit = window.matchMedia(MOBILE_BREAKPOINT).matches
          ? MAX_BUBBLES_MOBILE
          : MAX_BUBBLES_DESKTOP;
        const words = data.displayWords.slice(0, bubbleLimit);
        const highestCount = words[0] ? words[0].count : 1;
        summary.textContent = `${data.displayWordCount.toLocaleString()} curated terms / ${data.displayWordUses.toLocaleString()} uses`;
        const nodes = words.map(({ word, count }) => {
          const size = 42 + Math.sqrt(count / highestCount) * 58;
          const fontSize = Math.max(7, Math.min(15, (size - 10) / (word.length * 0.55)));
          const bubble = document.createElement("button");
          bubble.type = "button";
          bubble.className = "word-map__bubble";
          bubble.style.setProperty("--bubble-size", `${size}px`);
          bubble.style.setProperty("--bubble-font-size", `${fontSize}px`);
          bubble.textContent = word;
          bubble.title = `Click to disturb the word cloud. ${word} appears ${count.toLocaleString()} time${count === 1 ? "" : "s"}.`;
          bubble.setAttribute("aria-label", `${word}, ${count} uses. Activate to disturb the word cloud.`);
          bubbles.appendChild(bubble);
          return { element: bubble, radius: size / 2, x: 0, y: 0, vx: 0, vy: 0, positioned: false };
        });
        startKineticLayout(bubbles, nodes);
        map.dataset.loaded = "true";
      })
      .catch(() => { summary.textContent = "Word statistics will appear after the next content update."; });
  }

  if (typeof document$ !== "undefined") document$.subscribe(renderWordMap);
  else document.addEventListener("DOMContentLoaded", renderWordMap);
})();
