// Study-tools carousel: arrow scrolling + a cyan "active" glow on the card
// nearest the centre of the track (like the reference mock).
(function () {
  "use strict";

  var root = document.querySelector("[data-carousel]");
  if (!root) return;

  var track = root.querySelector("[data-carousel-track]");
  var cards = Array.prototype.slice.call(track.querySelectorAll(".carousel-card"));
  var prev = root.querySelector("[data-carousel-prev]");
  var next = root.querySelector("[data-carousel-next]");
  if (!cards.length) return;

  function step() {
    if (cards.length < 2) return track.clientWidth;
    return cards[1].offsetLeft - cards[0].offsetLeft;
  }

  function markActive() {
    var centre = track.scrollLeft + track.clientWidth / 2;
    var best = cards[0];
    var bestDist = Infinity;
    cards.forEach(function (card) {
      var cardCentre = card.offsetLeft + card.offsetWidth / 2;
      var dist = Math.abs(cardCentre - centre);
      if (dist < bestDist) {
        bestDist = dist;
        best = card;
      }
    });
    cards.forEach(function (card) {
      card.classList.toggle("is-active", card === best);
    });
  }

  prev.addEventListener("click", function () {
    track.scrollBy({ left: -step(), behavior: "smooth" });
  });
  next.addEventListener("click", function () {
    track.scrollBy({ left: step(), behavior: "smooth" });
  });

  var raf;
  track.addEventListener("scroll", function () {
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(markActive);
  });
  window.addEventListener("resize", markActive);

  // Start with the 2nd card centred, so cards peek on both sides.
  var startCard = cards[Math.min(1, cards.length - 1)];
  track.scrollLeft = startCard.offsetLeft - (track.clientWidth - startCard.offsetWidth) / 2;
  markActive();
})();
