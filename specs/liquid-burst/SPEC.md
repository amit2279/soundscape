# Liquid burst lab — build spec

Status: not started. Written 20 Nov 2026 for a fresh session.
Owner: Amit. Project: Soundscape (https://soundscape.zone), repo `amit2279/soundscape`, branch `main`.

Read `HANDOFF.md` first for the project's rules and history. This file covers only this one feature.

## 1. What we are making

A new test bench page, `liquid-lab.html`, in the style of the other labs (`laser-lab.html`, `blackhole-lab.html`, `plasma-lab.html`). It shows thick coloured liquid seen from directly above, in macro. Beads of pigment sit on the surface; on the music's big moments a bead bursts and its colour spreads outward, the leading edge breaking into fine fingers and thousands of glittering grains, then everything drifts and settles.

It is a lab first. It only gets merged into `index.html` as a Soundscape mode after Amit approves the look.

The reference is a 5.6 second screen recording Amit supplied. Seven frames from it are in `ref/` next to this file (see section 9 for why they may need to be attached by hand). They are **inspiration only**. Standing project rule: original visuals, never a copy of someone else's work. Match the behaviour and the feeling, not the frames.

## 2. Amit's words

> "analyze this effect and tell me how we can re create it ? but with absolute organic motion we can even use external library for liquid motion to achieve this 'color dissipating' effect"

The two hard requirements in that:

1. **Absolute organic motion.** Nothing keyframed, nothing that moves on a visible formula. Colour must go where a simulated flow carries it.
2. **Colour dissipating.** Pigment that spreads, thins, stains what it passes over and fades into the liquid.

## 3. What the reference shows

Three shots, each the same event with different colours.

| Time (approx) | Shot | What happens |
|---|---|---|
| 0.0–0.25 s | Orange bead on purple, yellow haze | Bead at rest inside a clear shell. Background is far out of focus, with round bokeh discs. `ref/01-bead-at-rest.jpg` |
| 0.25–2.7 s | Black pigment on pink/magenta | Bead ruptures by the first few frames, radius roughly doubles in about 0.3 s, then slows. Edge tears into a fringe of yellow grains. `ref/02-black-burst-sequence.jpg`, `ref/04-still-fingering-edge.jpg` |
| 2.7–5.6 s | Magenta bead on orange/indigo | Bead holds for ~0.1 s, shell breaks, magenta floods out; a pale ring of bright grains rides the front; a few droplets are thrown clear. Fills the frame by ~3.4 s, then drifts. `ref/03-magenta-burst-sequence.jpg`, `ref/05-still-grain-ring.jpg`, `ref/06-still-settled.jpg`, `ref/07-still-bead-shell.jpg` |

Anatomy of one burst, in order:

1. **Bead.** A dome of saturated pigment, with a thin clear rim (the shell) and a soft shadow on one side. Slight surface texture: tiny bubbles, a crease or two.
2. **Rupture.** Fast. Most of the expansion happens in the first 5–10 frames at 60 fps. It is not perfectly round: it leans to one side.
3. **Front.** The spreading edge is the richest part. It is not a line. It is a band where the pigment breaks into radial fingers and loose grains, brightest at the very front (a pale, almost white ring in the magenta shot, yellow in the black shot).
4. **Interior.** Behind the front the colour is dense and fairly flat, with faint darker veins.
5. **Ejecta.** A handful of separate droplets leave the front and sit as small clear lenses.
6. **Settle.** Motion decays over 1–2 s to a slow drift. The underlying colours are left stained.

Lens and light:

- Shallow depth of field. Sharp in the middle distance of the frame, soft towards the corners and in the background.
- Every grain carries a tiny specular highlight; grains twinkle as they move.
- Saturated palette of two to four colours per shot, always with one dark or one very light colour for contrast.
- No hard black background except where the pigment itself is black.

## 4. Approach

Three layers that all read the same velocity field, so they move as one thing.

### 4.1 Liquid: 2D GPU fluid simulation

Standard "stable fluids" on the GPU (the method used by Pavel Dobryakov's WebGL Fluid Simulation, MIT licence). Write our own passes inside three.js so it fits the project; do not paste that project in. Use it as a method reference only.

Textures (ping-pong pairs, `HalfFloatType` for phone support, linear filtering where available):

| Texture | Suggested size | Holds |
|---|---|---|
| velocity | 256–384 on the short side | xy velocity |
| pressure | same as velocity | pressure |
| divergence, curl | same | scratch |
| dye | 1024 on the short side | rgb pigment, a = thickness |

Per frame, in this order: curl → vorticity confinement → divergence → pressure solve (about 20 Jacobi iterations) → subtract gradient → advect velocity → advect dye. Use a fixed simulation step, decoupled from the display frame rate, with a cap so a slow frame does not explode the sim.

Additions that make it read as paint instead of smoke:

- **Viscosity and drag.** Velocity dissipation high enough that a burst stops within 1–2 s. Dye dissipation very low, so colour stays.
- **Burst = divergence source.** A burst injects positive divergence in a disc at the bead for a few steps (a real outward push in every direction), not a single directional splat. Add a small random lean so it is never perfectly round.
- **Fingering at the front.** Perturb the outward push with fine angular noise, and add curl noise scaled by the dye gradient so only the edge breaks up. Tune until the edge tears into fingers; a clean expanding circle is a fail.
- **Staining.** New dye mixes subtractively-ish with what is there (do not just add RGB to white). A simple approach: keep pigment as absorption and convert to colour at display time.

### 4.2 Grains: GPU particles carried by the flow

- 200k–400k points (quality slider scales this), positions in a float texture, updated in a fragment pass that samples the velocity texture. `GPUComputationRenderer` ships with three 0.147 under `examples/js/misc/`; check the file exists on jsDelivr at that version before relying on it, otherwise write the two passes by hand.
- Grains are born at a bead when it bursts, concentrated at the front, with a little extra outward speed so they lead the dye. They slow with the liquid and then only drift.
- Each grain: size varies, colour is the pigment colour pushed towards a pale highlight, brightness flickers with its own phase and with its speed.
- A few dozen larger "droplet" sprites per burst for the ejecta: clear lens look, faked (bright rim, dark edge, small highlight). No real refraction in version 1.

### 4.3 Bead

Before it bursts, a bead is drawn as a shaded dome sprite over the dye: pigment colour, thin clear rim, soft side shadow, a little noise for texture. It swells slightly as the build-up rises, then is replaced by the burst. Beads are placed by the scheduler in section 5.

### 4.4 Display and lens

- Final pass turns dye into colour, adds a soft height-based shading from the dye thickness gradient (so the liquid has body), then grains on top, additive.
- Depth of field faked in screen space: blur radius grows with distance from a focus point near the active bead. Bokeh discs for out-of-focus grains if affordable.
- Bloom with the existing `UnrealBloomPass`, restrained. A hue-keeping final pass like the labs use (`c/max(1,max(c.r,c.g,c.b))`) so piled-up light never goes white. Amit has rejected blown-out white several times.
- Camera: looking straight down, orthographic or a long lens. Drag to pan, scroll to zoom, both eased (heavy, slow to settle), as in the other labs.

## 5. How sound drives it

Use the lab analysis already in `laser-lab.html` (`analyse(data,sr)` → 48 bands: `lev` level per band per frame, `on` onsets, `hits` whole-mix hits). Copy that scaffold, the transport, the demo-track synth and the `window.__lab` test hook.

| Sound | Drives |
|---|---|
| Whole-mix hits (`hits`) and strong low-band onsets | A bead bursts. Strength of hit → strength of push. |
| Rising energy before a hit | The next bead swells. |
| Which bands are loudest at the hit | Which colour bursts and roughly where (low bands near the centre, high bands further out). |
| Per-band level | Brightness and twinkle of grains of that band's colour. |
| Bass level | Slow overall pressure: gentle breathing push from existing pools. Keep it small. |
| Silence / no song | Idle state: slow drift, an occasional small bead bursting on its own clock. |

**Rule, non-negotiable:** music may trigger events and change colour and brightness. It must never directly move the liquid or the grains frame by frame. All motion comes from the simulation. This is the same rule as the smoke in the laser lab ("the smoke should be free flowing organic smoke").

Limit bursts so the screen does not fill and go muddy: a minimum gap between bursts (start at 0.35 s), a cap on live beads, and very slow global dye fade so old colour makes room.

## 6. Controls for the lab

Bottom bar like the other labs: Play/pause, seek, time, Song upload, plus:

- Colour set button (key C): four to six palettes. Each palette is a base liquid colour plus three or four pigments, one of them dark or near-white.
- Quality slider: scales sim resolution and grain count.
- Click on the picture: burst a bead there (for testing the look without music).

## 7. Project rules that apply

- Single static HTML file, vanilla JS, three.js **0.147.0 UMD from jsDelivr** (`examples/js/...`). GLSL in template literals.
- Motion is always eased, never snapped.
- Honest status: say what was checked and what was not. Headless checks are ~3 fps stills; they cannot judge motion. Motion is Amit's call in the artifact.
- One step at a time. Publish, wait for feedback, then continue.
- Keep `HANDOFF.md` updated with a new section for this lab.
- Known traps from this codebase: `//` comments on long shared lines break things (use `/* */`); `half` is a reserved word in GLSL ES; a `const` declared later in the file cannot be used at startup.
- Labs are not deployed (the live site serves `dist/` only). Nothing here needs a Vercel deploy until a merge is approved.
- Commit messages end with the session's attribution lines.

## 8. Milestones

Stop after each one and show Amit.

1. **Liquid only.** Fluid sim running, click to burst, dye spreads and stains, edge fingers. No music, no grains. Pass: the edge is visibly ragged and the motion looks like liquid, not smoke.
2. **Grains.** Particles carried by the flow, pale glitter ring at the front, twinkle.
3. **Sound.** Scheduler from section 5, demo track and upload, idle state.
4. **Bead and lens.** Bead sprite with swell, focus blur, bloom, palettes.
5. **Polish and performance.** Quality slider, phone check, ejecta droplets.
6. Only if approved: merge into `index.html` as a mode, with a port script like `tools/port_blackhole.py`.

## 9. Testing and the reference images

- Headless harness: `tools/test/lab.py` (Playwright, software GL). It expects the lab copied to a local file with the CDN path swapped for a local `node_modules/three@0.147.0`; see the comments at the top of the script and section "Headless tests" in `HANDOFF.md`. A new workspace needs `pip install playwright`, `playwright install chromium` and `npm i three@0.147.0`.
- Float render targets under software GL can behave differently from a real GPU. If the sim shows black in the harness, check extension support before assuming the shader is wrong.
- The reference frames are deliberately **not committed**: the repo is public and the frames come from someone else's footage. Amit has them as files; attach them to the new session, or drop them in `specs/liquid-burst/ref/` locally (the folder is git-ignored).

## 10. Open questions for Amit

- Top-down flat view only, or should the camera ever tilt?
- Should the liquid hold all colour for the whole song (a painting that builds up), or slowly clear?
- Is a faked droplet shell acceptable in version 1, or is the glassy bead the main attraction?

## 11. Not in scope

- Real refraction or 3D liquid.
- SoundCloud or any streaming source.
- Changes to existing modes.
