/* Agentic Brain homepage — animations (framework-free) */
(function () {
  function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  onReady(function () {
    var root = document.querySelector(".ab-wrap");
    if (!root) return;

    /* ---- Hide Odoo's theme header/footer on this page (bulletproof, no :has needed) ---- */
    document.body.classList.add("ab-home-page");

    /* ---- Rotating headline word ---- */
    var words = ["itself.", "on autopilot.", "autonomously.", "24/7."];
    var wordEl = document.getElementById("ab-word");
    if (wordEl) {
      var wi = 0;
      setInterval(function () {
        wi = (wi + 1) % words.length;
        wordEl.textContent = words[wi];
      }, 2600);
    }

    /* ---- Scroll reveal ---- */
    var revs = root.querySelectorAll(".rev, .revL, .revR, .revS");
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            io.unobserve(e.target);
          }
        });
      }, { threshold: 0.15 });
      revs.forEach(function (r) { io.observe(r); });
    } else {
      revs.forEach(function (r) { r.classList.add("in"); });
    }

    /* ---- Count-up stats ---- */
    function animCount(node, target, suffix, dur) {
      if (!node) return;
      var t0 = performance.now();
      function tick(now) {
        var p = Math.min(1, (now - t0) / dur);
        var e = 1 - Math.pow(1 - p, 3);
        var v = Math.round(e * target);
        node.textContent = v.toLocaleString() + suffix;
        if (p < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    }
    var stats = document.getElementById("ab-stats");
    if (stats && "IntersectionObserver" in window) {
      var done = false;
      var so = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting && !done) {
            done = true;
            animCount(document.getElementById("st-hours"), 10000, "+", 1700);
            animCount(document.getElementById("st-faster"), 63, "%", 1700);
            animCount(document.getElementById("st-rev"), 3, "\u00D7", 1700);
            so.disconnect();
          }
        });
      }, { threshold: 0.4 });
      so.observe(stats);
    }
  });
})();
