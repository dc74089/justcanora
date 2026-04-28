(() => {
  'use strict';

  const N              = 4000;
  const STRAY          = 0.15;
  const ATTRACT        = 0.030;
  const ATTRACT_MAX    = 0.50;
  const WANDER         = 0.14;
  const WANDER_TURN    = 0.05;
  const WANDER_FALLOFF = 40;
  const SETTLE_RADIUS  = 6;
  const DAMPING_NEAR   = 0.80;
  const DAMPING_FAR    = 0.93;
  const MAX_SPD        = 4.0;
  const STRAY_WANDER   = 0.07;
  const STRAY_TURN     = 0.025;
  const STRAY_MAX_SPD  = 0.8;
  const SCATTER_SPD    = 3.5;
  const SAMPLE         = 4;
  const PARTICLE_R_MIN = 0.5;   // minimum particle radius (px)
  const PARTICLE_R_MAX = 1.4;   // maximum particle radius (px)
  const HALO_MULT      = 4;     // halo radius = particle radius × this
  const HALO_ALPHA     = 0.06;  // additive alpha for the glow ring pass

  // Matches .happygradtext: linear-gradient(-45deg, #ff37e4, #ee7752, #e73c7e, #23a6d5, #23d5ab)
  const PALETTE = [
    { h: 170, s: 100, l: 55 },  // mint/teal
    { h: 195, s: 100, l: 60 },  // cyan
    { h: 250, s:  90, l: 72 },  // periwinkle
    { h: 300, s: 100, l: 70 },  // violet-pink
    { h:  50, s: 100, l: 65 },  // warm gold accent
  ];
  const NC = PALETTE.length;

  class Particle {
    constructor(i) {
      this.x         = Math.random() * innerWidth;
      this.y         = Math.random() * innerHeight;
      this.vx        = (Math.random() - 0.5) * 2;
      this.vy        = (Math.random() - 0.5) * 2;
      this.colorIdx  = i % NC;
      this.r         = PARTICLE_R_MIN + Math.random() * (PARTICLE_R_MAX - PARTICLE_R_MIN);
      this.tx        = null;
      this.ty        = null;
      this.active    = false;
      this.wander    = Math.random() * Math.PI * 2;
      this.pulse     = Math.random() * Math.PI * 2;
      this.pulseRate = 0.025 + Math.random() * 0.025;
    }

    setTarget(x, y) {
      this.tx     = x + (Math.random() - 0.5) * 4;
      this.ty     = y + (Math.random() - 0.5) * 4;
      this.active = true;
    }

    release() {
      this.tx = null; this.ty = null;
      this.active = false;
    }

    tick() {
      if (this.active) {
        const dx   = this.tx - this.x;
        const dy   = this.ty - this.y;
        const dist = Math.hypot(dx, dy);

        if (dist > 0.5) {
          const f = Math.min(dist * ATTRACT, ATTRACT_MAX);
          this.vx += (dx / dist) * f;
          this.vy += (dy / dist) * f;
        }

        const wanderScale = Math.min(dist / WANDER_FALLOFF, 1.0);
        if (wanderScale > 0.01) {
          this.wander += (Math.random() - 0.5) * WANDER_TURN * 2;
          this.vx += Math.cos(this.wander) * WANDER * wanderScale;
          this.vy += Math.sin(this.wander) * WANDER * wanderScale;
        }

        const damping = dist < SETTLE_RADIUS ? DAMPING_NEAR : DAMPING_FAR;
        this.vx *= damping;
        this.vy *= damping;

        const spd2 = this.vx * this.vx + this.vy * this.vy;
        if (spd2 > MAX_SPD * MAX_SPD) {
          const inv = MAX_SPD / Math.sqrt(spd2);
          this.vx *= inv;
          this.vy *= inv;
        }

      } else {
        this.wander += (Math.random() - 0.5) * STRAY_TURN * 2;
        this.vx += Math.cos(this.wander) * STRAY_WANDER;
        this.vy += Math.sin(this.wander * 1.41) * STRAY_WANDER;

        const spd2 = this.vx * this.vx + this.vy * this.vy;
        if (spd2 > STRAY_MAX_SPD * STRAY_MAX_SPD) {
          const inv = STRAY_MAX_SPD / Math.sqrt(spd2);
          this.vx *= inv;
          this.vy *= inv;
        }

        if (this.x < -15)                   this.x = innerWidth  + 15;
        else if (this.x > innerWidth  + 15)  this.x = -15;
        if (this.y < -15)                   this.y = innerHeight + 15;
        else if (this.y > innerHeight + 15)  this.y = -15;
      }

      this.x += this.vx;
      this.y += this.vy;
    }
  }

  // ── Offscreen canvas text sampling ──────────────────────────────────────────
  // Returns { pts, maxParticles } — maxParticles is the sum of data-particle-max
  // across all elements (Infinity if none specify it), used to cap swarm size.
  function sampleText(elements) {
    const off = document.createElement('canvas');
    const oc  = off.getContext('2d', { willReadFrequently: true });
    const pts = [];
    let totalMax = 0;
    let hasMax   = false;

    for (const el of elements) {
      const rect = el.getBoundingClientRect();
      if (rect.width < 2 || rect.height < 2) continue;

      const cs   = window.getComputedStyle(el);
      off.width  = Math.ceil(rect.width)  + 4;
      off.height = Math.ceil(rect.height) + 4;

      oc.clearRect(0, 0, off.width, off.height);
      oc.font         = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
      oc.textAlign    = 'center';
      oc.textBaseline = 'middle';
      oc.fillStyle    = '#fff';
      oc.fillText(el.textContent.trim(), off.width / 2, off.height / 2, off.width * 0.95);

      const { data } = oc.getImageData(0, 0, off.width, off.height);
      for (let py = 0; py < off.height; py += SAMPLE) {
        for (let px = 0; px < off.width; px += SAMPLE) {
          if (data[(py * off.width + px) * 4 + 3] > 100)
            pts.push({ x: rect.left + px, y: rect.top + py });
        }
      }

      if (el.dataset.particleMax !== undefined) {
        hasMax    = true;
        totalMax += parseInt(el.dataset.particleMax);
      }
    }

    return { pts, maxParticles: hasMax ? totalMax : Infinity };
  }

  // ── Assign text-forming targets ──────────────────────────────────────────────
  // { pts, maxParticles }: from sampleText — maxParticles caps active swarm count
  // swarmFraction (0–1): from data-particle-density on the panel
  function assignTargets(particles, { pts: targets, maxParticles }, strayN, swarmFraction = 1.0) {
    const order = particles.map((_, i) => i);
    for (let i = order.length - 1; i > 0; i--) {
      const j = (Math.random() * (i + 1)) | 0;
      [order[i], order[j]] = [order[j], order[i]];
    }

    if (!targets.length) { particles.forEach(p => p.release()); return; }

    const tgt = [...targets];
    for (let i = tgt.length - 1; i > 0; i--) {
      const j = (Math.random() * (i + 1)) | 0;
      [tgt[i], tgt[j]] = [tgt[j], tgt[i]];
    }

    const base   = Math.round((particles.length - strayN) * Math.min(1, Math.max(0, swarmFraction)));
    const swarmN = Math.min(base, maxParticles);
    for (let i = 0; i < swarmN; i++)
      particles[order[i]].setTarget(tgt[i % tgt.length].x, tgt[i % tgt.length].y);
    for (let i = swarmN; i < particles.length; i++)
      particles[order[i]].release();
  }

  // ── Most-visible panel ───────────────────────────────────────────────────────
  function currentPanel() {
    let best = null, bestV = -1;
    for (const p of document.querySelectorAll('.panel')) {
      const r = p.getBoundingClientRect();
      const v = (Math.min(r.bottom, innerHeight) - Math.max(r.top, 0)) / innerHeight;
      if (v > bestV) { bestV = v; best = p; }
    }
    return best;
  }

  // ── Bootstrap ────────────────────────────────────────────────────────────────
  function init() {
    const canvas = document.getElementById('particle-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const resize = () => { canvas.width = innerWidth; canvas.height = innerHeight; };
    resize();
    window.addEventListener('resize', () => { resize(); refresh(); });

    const particles = Array.from({ length: N }, (_, i) => new Particle(i));
    const strayN    = Math.round(N * STRAY);
    let swarming = [], straying = [...particles];

    const coreBuckets = Array.from({ length: NC }, () => []);

    function scatter() {
      for (const p of particles) {
        p.release();
        const angle = Math.random() * Math.PI * 2;
        const spd   = SCATTER_SPD * (0.4 + Math.random() * 0.6);
        p.vx = Math.cos(angle) * spd;
        p.vy = Math.sin(angle) * spd;
      }
      swarming = [];
      straying = [...particles];
    }

    function refresh() {
      const panel    = currentPanel();
      const textEls  = panel ? [...panel.querySelectorAll('.particle-target')] : [];
      const density  = panel ? parseFloat(panel.dataset.particleDensity ?? '1') : 1;
      assignTargets(particles, sampleText(textEls), strayN, density);
      swarming = particles.filter(p =>  p.active);
      straying = particles.filter(p => !p.active);
    }

    refresh();

    let scrolling = false;
    let debounce  = null;

    window.addEventListener('scroll', () => {
      if (!scrolling) { scatter(); scrolling = true; }
      clearTimeout(debounce);
      debounce = setTimeout(() => { scrolling = false; refresh(); }, 80);
    }, { passive: true });

    if ('onscrollend' in window) {
      window.addEventListener('scrollend', () => {
        clearTimeout(debounce);
        scrolling = false;
        refresh();
      });
    }

    let frame = 0;
    (function loop() {
      requestAnimationFrame(loop);
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      for (let b = 0; b < NC; b++) coreBuckets[b].length = 0;

      for (const p of swarming) {
        p.tick();
        p.pulse += p.pulseRate;
        coreBuckets[p.colorIdx].push(p);
      }
      for (const p of straying) {
        p.tick();
        p.pulse += p.pulseRate;
        coreBuckets[p.colorIdx].push(p);
      }

      // Halos: additive soft glow rings
      ctx.globalCompositeOperation = 'lighter';
      ctx.globalAlpha = HALO_ALPHA;
      for (let b = 0; b < NC; b++) {
        if (!coreBuckets[b].length) continue;
        const c = PALETTE[b];
        ctx.fillStyle = `hsl(${c.h},${c.s}%,${c.l}%)`;
        ctx.beginPath();
        for (const p of coreBuckets[b]) {
          ctx.moveTo(p.x + p.r * HALO_MULT, p.y);
          ctx.arc(p.x, p.y, p.r * HALO_MULT, 0, Math.PI * 2);
        }
        ctx.fill();
      }

      // Swarming cores: pulsing
      for (let b = 0; b < NC; b++) {
        const ps = coreBuckets[b];
        if (!ps.length) continue;
        let sum = 0;
        for (const p of ps) sum += 0.55 + 0.45 * Math.sin(p.pulse);
        ctx.globalAlpha = (sum / ps.length) * 0.75;
        const c = PALETTE[b];
        ctx.fillStyle = `hsl(${c.h},${c.s}%,${Math.min(c.l + 15, 90)}%)`;
        ctx.beginPath();
        for (const p of ps) {
          ctx.moveTo(p.x + p.r, p.y);
          ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        }
        ctx.fill();
      }

      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = 1;
      frame++;
    })();
  }

  document.readyState === 'loading'
    ? document.addEventListener('DOMContentLoaded', init)
    : init();
})();
