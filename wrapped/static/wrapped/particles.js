(() => {
  'use strict';

  const N              = 4000;   // total particle count
  const STRAY          = 0.15;   // default fraction of particles left as free-floating strays (0–1)
  const ATTRACT        = 0.040;  // per-frame force toward target, scaled by distance
  const ATTRACT_MAX    = 0.75;   // cap on attraction force so particles don't teleport
  const WANDER         = 0.05;   // lateral force while approaching target (lower = straighter path)
  const WANDER_TURN    = 0.015;  // how quickly wander direction drifts
  const WANDER_FALLOFF = 100;    // wander fades to zero within this many px of target
  const SETTLE_RADIUS  = 6;      // px — switch to strong damping once this close to target
  const DAMPING_NEAR   = 0.80;   // velocity multiplier per frame when within SETTLE_RADIUS
  const DAMPING_FAR    = 0.93;   // velocity multiplier per frame when outside SETTLE_RADIUS
  const MAX_SPD        = 6.0;    // px/frame speed cap for swarming particles
  const STRAY_WANDER   = 0.015;  // stray drift force (very slow glide)
  const STRAY_TURN     = 0.006;  // stray turning rate (near-linear drift)
  const STRAY_MAX_SPD  = 0.25;   // stray top speed (barely moving)
  const SCATTER_SPD    = 9.0;    // burst speed given to particles when a scroll scatter fires
  const SCATTER_DECAY  = 0.97;   // per-frame speed multiplier after scatter (lets burst carry across screen)
  const SAMPLE         = 4;      // pixel stride when sampling text from the offscreen canvas (higher = fewer targets)
  const PARTICLE_R_MIN = 0.3;   // minimum particle radius (px)
  const PARTICLE_R_MAX = 0.8;   // maximum particle radius (px)
  const HALO_MULT      = 2;     // halo radius = particle radius × this
  const HALO_ALPHA     = 0.4;  // additive alpha for the glow ring pass
  const BORDER_DEPTH   = 20;   // px — thickness of the border band
  const STRAY_DIM      = 0.2;  // 0–1 target brightness for stray particles (halo + core)
  const DIM_SPEED      = 0.04; // lerp rate toward target brightness (higher = faster transition)

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
      this.dim       = STRAY_DIM;
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
          const spd    = Math.sqrt(spd2);
          const capped = Math.max(spd * SCATTER_DECAY, STRAY_MAX_SPD);
          this.vx = (this.vx / spd) * capped;
          this.vy = (this.vy / spd) * capped;
        }

        if (this.x < -15)                   this.x = innerWidth  + 15;
        else if (this.x > innerWidth  + 15)  this.x = -15;
        if (this.y < -15)                   this.y = innerHeight + 15;
        else if (this.y > innerHeight + 15)  this.y = -15;
      }

      this.x += this.vx;
      this.y += this.vy;
      this.dim += ((this.active ? 1.0 : STRAY_DIM) - this.dim) * DIM_SPEED;
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
  // swarmFraction (0–1): fraction of ALL particles to activate; 1.0 = no strays.
  // Default density is (1 - STRAY), so omitting the attribute preserves the normal stray ratio.
  function assignTargets(particles, { pts: targets, maxParticles }, swarmFraction = 1.0) {
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

    const base   = Math.round(particles.length * Math.min(1, Math.max(0, swarmFraction)));
    const swarmN = Math.min(base, maxParticles);
    for (let i = 0; i < swarmN; i++)
      particles[order[i]].setTarget(tgt[i % tgt.length].x, tgt[i % tgt.length].y);
    for (let i = swarmN; i < particles.length; i++)
      particles[order[i]].release();
  }

  // ── Border shape generator ───────────────────────────────────────────────────
  // Generates exactly N points uniformly spaced around the perimeter so that
  // every active particle gets a unique target — no stacking, no gaps.
  // Each point has a random inward depth up to BORDER_DEPTH for an organic band.
  function generateBorderPoints() {
    const pts       = [];
    const w         = innerWidth;
    const h         = innerHeight;
    const perimeter = 2 * (w + h);

    for (let i = 0; i < N; i++) {
      const d = (i / N) * perimeter;
      let x, y;
      if (d < w) {                         // top edge →
        x = d;       y = Math.random() * BORDER_DEPTH;
      } else if (d < w + h) {              // right edge ↓
        x = w - Math.random() * BORDER_DEPTH; y = d - w;
      } else if (d < 2 * w + h) {          // bottom edge ←
        x = 2 * w + h - d; y = h - Math.random() * BORDER_DEPTH;
      } else {                             // left edge ↑
        x = Math.random() * BORDER_DEPTH; y = perimeter - d;
      }
      pts.push({ x, y });
    }
    return pts;
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
    let swarming = [], straying = [...particles];

    const swarmBuckets = Array.from({ length: NC }, () => []);
    const strayBuckets = Array.from({ length: NC }, () => []);

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
      const density  = panel ? parseFloat(panel.dataset.particleDensity ?? String(1 - STRAY)) : (1 - STRAY);
      const behavior = panel?.dataset.particleBehavior;

      if (behavior === 'border') {
        assignTargets(particles, { pts: generateBorderPoints(), maxParticles: Infinity }, density);
      } else {
        const textEls = panel ? [...panel.querySelectorAll('.particle-target')] : [];
        assignTargets(particles, sampleText(textEls), density);
      }

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

      for (let b = 0; b < NC; b++) swarmBuckets[b].length = strayBuckets[b].length = 0;

      for (const p of swarming) {
        p.tick();
        p.pulse += p.pulseRate;
        swarmBuckets[p.colorIdx].push(p);
      }
      for (const p of straying) {
        p.tick();
        p.pulse += p.pulseRate;
        strayBuckets[p.colorIdx].push(p);
      }

      ctx.globalCompositeOperation = 'lighter';

      // Halos — avgDim per bucket keeps swarm and stray independent
      for (let b = 0; b < NC; b++) {
        const c = PALETTE[b];
        ctx.fillStyle = `hsl(${c.h},${c.s}%,${c.l}%)`;

        if (strayBuckets[b].length) {
          let dimSum = 0;
          for (const p of strayBuckets[b]) dimSum += p.dim;
          ctx.globalAlpha = HALO_ALPHA * (dimSum / strayBuckets[b].length);
          ctx.beginPath();
          for (const p of strayBuckets[b]) {
            ctx.moveTo(p.x + p.r * HALO_MULT, p.y);
            ctx.arc(p.x, p.y, p.r * HALO_MULT, 0, Math.PI * 2);
          }
          ctx.fill();
        }

        if (swarmBuckets[b].length) {
          let dimSum = 0;
          for (const p of swarmBuckets[b]) dimSum += p.dim;
          ctx.globalAlpha = HALO_ALPHA * (dimSum / swarmBuckets[b].length);
          ctx.beginPath();
          for (const p of swarmBuckets[b]) {
            ctx.moveTo(p.x + p.r * HALO_MULT, p.y);
            ctx.arc(p.x, p.y, p.r * HALO_MULT, 0, Math.PI * 2);
          }
          ctx.fill();
        }
      }

      // Cores — pulse × dim per bucket
      for (let b = 0; b < NC; b++) {
        const c = PALETTE[b];
        ctx.fillStyle = `hsl(${c.h},${c.s}%,${Math.min(c.l + 15, 90)}%)`;

        for (const bucket of [strayBuckets[b], swarmBuckets[b]]) {
          if (!bucket.length) continue;
          let pulseSum = 0, dimSum = 0;
          for (const p of bucket) {
            pulseSum += 0.55 + 0.45 * Math.sin(p.pulse);
            dimSum   += p.dim;
          }
          ctx.globalAlpha = (pulseSum / bucket.length) * 0.75 * (dimSum / bucket.length);
          ctx.beginPath();
          for (const p of bucket) {
            ctx.moveTo(p.x + p.r, p.y);
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
          }
          ctx.fill();
        }
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
