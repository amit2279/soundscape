# Soundscape: handoff for the next agent

Written 2026-11-13 by the agent that built it. Read this before touching `index.html`.

## 1. What it is and where it lives

Soundscape turns a song into 3D worlds you ride through. Live at https://soundscape.zone.

- **One file**: `index.html` (about 252 KB, about 3,050 lines). Vanilla JS, no build step, no modules.
- **three.js 0.147.0 UMD** from jsDelivr (`build/three.min.js` plus `examples/js` CopyShader, LuminosityHighPassShader, Pass, EffectComposer, RenderPass, ShaderPass, UnrealBloomPass). Stay on 0.147: later versions drop `examples/js`.
- **Repo**: `amit2279/soundscape`, branch `main`. Branch `runner-backup-2026-11-11` holds a removed "Runner" world with rigged characters; do not merge it.
- **Hosting**: Vercel static project `soundscape`. The project is NOT linked to Git. Pushing does not deploy. The owner redeploys with `npx vercel --prod`, or links the repo in Vercel Settings → Git.
- **Claude artifact** (the owner's working preview): slug `6b45be5e-2779-4e3a-8fe4-4d4f1b2991d7`, title "Soundscape", capability `downloads`. Publish `index.html` to it after every change; pass the last version as `base_version`.
- `assets/` holds CC0 character and animation GLBs from the Runner experiment. Unused by the main build.

## 2. The owner's standing preferences

- Maximum psychedelic impact; everything reacts to sound.
- **Motion is always eased, never snapped.** Do not wire raw amplitude straight to geometry. Set a target and ease toward it (see 5.3).
- Cameras always ease. Beat zoom and shake are off (`CAM_PULSE=false`); keep it off.
- Original visuals only. References are inspiration; never reproduce a named artist's work.
- Glass UI, toolbars slide (never fade). He reviews by using it and sends artifact comments or screenshots.
- He wants honest status: say what was checked and what was not.

## 3. How to work on it

- Edit with small Python scripts that do exact string replacement with `assert s.count(old)==1`. The file is too big to rewrite; never regenerate it.
- **Trap that has bitten twice**: several statements often share one long line. If you append a `// comment` mid-line you comment out the rest of the line. Put comments at the true end of a line, or use `/* */`.
- GLSL lives inside JS template literals. `${GLSL_COMMON}`, `${BEND}`, `${GEO}` are JS interpolations. `#define` must start its own line.
- GLSL ES 1.0 (WebGL1 style): no dynamic loop bounds, `uSpec[int]` needs a constant or loop index in some drivers; the code uses `int(floor(x))` indices and it works on the targets tested.
- **Headless test**: `/home/claude/mc/test/run.py` (Playwright, SwiftShader). Recreate if the workspace is gone: serve the folder, load a copy of `index.html` with the CDN URL rewritten to a local `node_modules/three`, evaluate JS strings in order, `shot:name` saves a screenshot. Inject debug hooks by `sed`-replacing the line `app.dataset.world=world; app.dataset.mode=mode;` near the end of the script.
  - Start the demo with `document.querySelector('#btnDemo').click()`.
  - Headless runs at about 3 fps and `dt` is clamped to 0.05, so timed things take far longer than real time. Set uniforms directly to test an end state.
  - Ignore console lines about "GPU stall" and font fetch failures.
  - If a hook is "not defined", the script threw at load: run with no actions and read the `PAGEERROR`.
- You can only see still frames. The owner judges motion and audio sync. Say so.
- Commit messages end with the two attribution lines the session provides.

## 4. File map (search for these headers)

`layout constants` → `themes` → `renderer` → `sky` → `ground` → `buildings` → parks → `traffic` → `particle terrain` → `abyss` → `Loom` → `Temple`/`Mandala` (hidden, code kept) → `wormhole` → Tunnel (`const tun`) → Illusions (`const ill`, then particles `const part`) → `post` → `kaleidoscope planet` → `demo track` → `analysis` → `city` (build) → `audio transport` → `UI` → `loading` → `frame loop`.

## 5. Architecture

### 5.1 Audio analysis (done once per song, before playback)

`analyse()` decodes the file, runs its own FFT per frame (`A.fps` frames per second) and stores:
- `A.spec`: 12 log bands, 30 Hz to 16 kHz, per frame. `A.bass`, `A.mid`, `A.high`, `A.inten` per frame.
- `A.beats` (`{t,s}` from spectral flux), `A.bpm` (autocorrelation), `A.drops` (times), `A.segs` (districts).
The whole song is known in advance, so worlds can show the future (city blocks, terrain) and schedule events exactly.
Two demo tracks are synthesised in a Web Worker (`synthDemo`, `synthHouse`).

### 5.2 The shared uniform object `U`

Every material uses `uniforms:U` (one object, so one update feeds everything). Key entries:
`uTime`, `uCam`, `uBands` (bass, mid, high), `uSpec[12]`, `uSpecTex` (12×1 texture for fragment shaders: `lvl(band)`), `uPulse` (beat envelope 0..1), `uPlay`, `uNitro`, `uNeon`, `uDay`, `uPlanet`, theme colours `uA uB uWarm uCool uSkyTop uSkyMid uHorizon uFog`, `uFogD`, `uAsp`, `uPtr` (eased pointer), plus per-world ones (`uWormZ`, `uTunZ uTunW uTunD uTunA uTunB uTunF`, `uIllA uIllB uIllMix uIllT uIllFade`, `uPA uPB uPMix uPShow uSpecS[12] uBassS`, `uLoom*`).
In the frame loop `sb` and `sI` are smoothed bass and intensity, `pulse` the beat envelope.

### 5.3 Eased response (the pattern to reuse)

`uSpecS[12]` and `uBassS` are eased copies of the spectrum: each frame `s += (target - s) * min(1, dt*k)` with k about 1.1 to 1.6. Surfaces read the eased copy; colour and glow read the instant `uSpec`. This is currently updated only inside the Illusions block. **Planned**: move that update out so every world can use it, then drive the skyscraper heights (`aBld`/Nitro stretch in the building vertex shader) from it.

### 5.4 Worlds

`WORLDS=['city','terrain','abyss','worm','tun','ill','loom']`, switched by `setWorld(w)`; tabs are `#worldSeg button[data-world]`. Camera modes `cruise`, `surf` (labelled Fly), `skyline`, `planet` via `setMode(m)`. In the frame loop each world has a `xxxOn` boolean; full-screen worlds hide the city meshes.

- **City**: instanced boxes (`BoxGeometry(1,1,1,6,1,6)`, corners rounded in the vertex shader), one `InstancedMesh` per chunk, all window/sign/neon detail drawn in the fragment shader from per-instance attributes (`aDim`, `aBld`, `aInfo`, `aShape`). `blocks` texture marks lot types; `blockH` holds roof heights for collision (`blockTop(x,z)`). Layout: `AV` avenue width, `PX`/`PZ` block pitch, `BW` block width, `SZ` side street, `COLS` per side, `ROWS` along the song. `SPEED` = world units per second of song.
- **Daylight** is a theme with `day:1` → `uDay`. Sky gets a sun, buildings get per-building paint, ground goes grey, bloom is reduced.
- **Parks** (`buildParks`): lots of type 1 get a hill mesh, instanced low-poly trees and a turning sculpture; `parkH(x,z)` gives ground height.
- **Planet**: `BEND` chunk wraps world space round a sphere of radius `PR`=640 by `uPlanet`.
- **Terrain**: particles, generated as the song progresses.
- **Abyss**: generative sea creatures.
- **Loom**: 12 pipes woven round a torus, `loomSt`/`loomStep` choreography. Symmetry comes from animating only shared parameters. Shine must stay under about 10%.
- **Wormhole** (`worm`): full-screen quad, polar mapping `z=.9/r`, sections of 7 depth units each pick a texture type `ty` 0..8. Type 1 is switched off (remapped to 4). Bends: the centre offset `tn*(1-exp(-z*.2))` solved by 3 fixed-point iterations; `tn` is thresholded value noise of `uWormZ`.
- **Tunnel** (`tun`): full-screen quad, 64-step ray march of a tube round `path(z)` with a flat floor. `wall(style, th, z, aa, t)` has 6 styles (0 dots, 1 glowing motes, 2 spiral bands, 3 nested diamonds, 4 liquid contours, 5 rings × rays; style 5 is switched off, the cycle is 0 to 4). `uTunA` is the current style, `uTunB` the incoming one, and `uTunF` is a front distance: pixels further than `uTunF` show B. `tunNext()` starts a change (auto every 48 beats, click, or G). `tunV` is eased speed. `uTunD` is the slow sideways dot drift (18 s still, about 20 s drifting, direction alternates).
- **Illusions**: scenes 0..4 are drawn in the `ill` quad shader (`sLines sDots sDash sTube sRoad`; `sFlow`, id 5, is switched off). Scenes 6..11 are one `THREE.Points` cloud (`part`, about 44,000 points, 14,000 with reduced motion). `shape(id)` returns a position on a surface plus visibility in `w`. Particle→particle: `uPA`→`uPB` with `uPMix`, each point leaves at its own time. Any other change: `illPend` + `illK` fade to black, `illApply` swaps in the dark. Never automatic: click or G only. `PART_CAM` holds one camera per structure; tunnels ignore the mouse.

### 5.5 Cameras

`tOff`/`tLk` are targets; `off`/`lk` ease toward them. Free roam (`fr`) starts on the first arrow/WASD press in City or Terrain: velocity-based car with inertia and lateral grip, wall sliding via `blockTop`, Q/E height, Shift boost, completely independent of song time. Arrow keys must never seek (`[` and `]` do). A NaN guard resets the camera if a bad number appears. Scroll zoom (`zoomT`/`zoomK`) changes field of view for City, Terrain, Abyss, Loom; `fovBase` is the eased un-zoomed value.

### 5.6 Post

RenderPass → kaleidoscope pass → light rays (kaleidoscope planet only) → UnrealBloomPass. Bloom only at quality ≥ 3. `QDPR=[0,.4,.55,.75,1,1.75]` is the render scale per quality level.

## 6. Performance rules that matter

- Geometry is instanced; per-object variety comes from attributes plus shader maths, not from more meshes.
- Detail is procedural in fragment shaders; there are no image textures except tiny data textures (`uSpecTex`, block maps).
- Full-screen shader worlds cost per pixel: keep ray-march steps low (Tunnel 64, funnel 80), avoid loops over many layers, fade fine patterns to their average colour far away instead of anti-aliasing them.
- Never allocate in the frame loop; reuse vectors.
- Bloom makes dense bright points blow out: keep point brightness and size modest (see `vH` and `gl_PointSize` in `part`).
- Rounded buildings raised triangles per plain tower from 12 to about 190. If frame rate drops, lower the segment count in that `BoxGeometry`.

## 7. Open work, in the owner's priority order

0. **Coaster world: first version built 2026-11-14** (`world==='coast'`, section header "Coaster"). `coastPlan()` integrates the ride at 60 samples per second of song into `COAST.px/py/pz/yaw/pit/rol/vel`: lift hill for 6 s before each drop, pitch -1.22 on the drop, a loop 3.4 s after every second drop (pitch turns 2π), barrel rolls on hard accents, wandering yaw and hills from value noise scaled by eased intensity, speed `v += (-46*sin(pitch) + (vt-v)*.55)*dt`. `coastFrame(t)` gives position and the frame. Rails are five ribbons in one mesh; ties, gates (ring geometry with 3, 4, 6, 56 segments), shards and solids are `InstancedMesh`es using `coastObjMat` with per-instance `aI=(time, hue, seed, mode)`; instances further than about 26 s of song from now are culled in the vertex shader. `coastStep` sets the look direction (eased mouse), `coastCam` overrides the camera after the normal camera code. Checked only in still frames. Next: motion blur, supports under the track, more object types, tune drop steepness and loop size with the owner.
0b. **`coaster-lab.html` (2026-11-14): the physics rebuild, as a separate test page.** The owner found the in-app Coaster unnatural, so the next version is being tuned here before it is ported into `index.html` to replace `coastPlan`. Standalone file, own small analysis and demo synth. `buildRide(A)` lays the track out in space in 0.4 m steps: speed from energy with drag; curvature from target g at the current speed (`kFor`), smoothed over a few metres; elements `hill`, `turn`, `loop` (teardrop), `corkscrew`, `boost`, `liftAndDrop`. `liftAndDrop(td)` solves the chain speed by fixed-point iteration so the crest (pitch passing -30 degrees) lands on the song's drop. Report on the demo: 1,444 m, 121 km/h, +4.4 g / -0.6 g, drops within 0.11 s. Track is two tube rails, a spine, three-piece ties every 1.2 m, support columns. Objects only on big moments: six torus gates per drop, one gate per top accent, a few solids kept clear of the track. Rider camera: looks ahead, head lag, g-force seat offset, speed rattle, no mouse look. Published as its own artifact "Coaster lab" (slug `c68270d2-057b-4b14-83d6-67b9296d41d3`). Second pass after owner feedback: gravity constant raised to 14 (he wants drops to bite), lifts up to 92 m, pillars removed, rails are dark tubes with thin neon line tubes along both rails and the spine (colour flows along the track), connectors are an open yoke frame of six boxes every 2.4 m, gates are tori stretched 4x along the track and placed in series (10 per drop, 5 per top accent) with rotation and scale delayed per gate (`aI.z` is the phase), camera lowered to 0.6 m with a wider lens and a slight downward look so the track fills the frame. Owner called the first pass "genius"; second pass awaiting his feedback. Third pass: gate rotation is inertia-driven (`spinV` gets an impulse per beat and friction back to a slow turn; `uSpA` is the angle, `uSpB`/`uSpC` are trailing copies used for the delay down a series), gate and neon-line glow follow `uBeat`, connectors are an open five-segment cradle with no bar above the rails. Fourth pass: two spines instead of one (each with two neon lines), connector is one smooth curve of 14 short segments, field of view reduced to 70 to 86 degrees because the owner felt the track ahead looked too far away (perspective distortion from a wide lens). Fifth pass: stretches of track between drops alternate between a tunnel (a tube mesh of radius 6.5 m swept round the track, `tunMat(style)` with motes, spiral bands or liquid contours, additive, double-sided) and a particle field (2,600 points round the track, `fieldMat`). Chrysanthemum fireworks (`fireMat`): one `Points` object, each burst is 190 rays of 4 trailing points, centred where the train will be 0.85 s after a strong beat and exploding on that beat, three on each drop; age comes from song time so seeking works. `R.fx` lists tunnel and burst times for testing. **Fireworks are switched off** (`FIREWORKS=false` in `buildWorld`): the owner found them too close and too frequent; when re-enabled they must sit outside the track and fire rarely. Still to do: motion blur, sound, then port into `index.html`.
1. **(Original brief for the coaster, kept for reference.)** Reference is an 18 s stock clip (iStock, watermarked, so it is licensed footage: use it as a benchmark for feel, do not copy its designs). What it shows: a first-person roller-coaster ride on a twisting rail made of 5 to 6 parallel white-cyan glowing lines with magenta cross-ties and supports; the track banks, climbs, dives and loops; other track sections cross in the distance; flat neon shards (triangles, quads) in red, green, cyan, orange float and tumble; you fly through gates of nested concentric outlines (triangles, squares, rings) in one colour each; heavy bloom and motion blur on black. Suggested build: a real 3D world (not a quad shader), track as a Catmull-Rom spline with banking from curvature, rails as instanced tube strips, ties instanced along the spline, camera locked to the spline frame with eased roll, speed from slope plus eased energy, gates placed on beats and drops (the analysis knows them in advance), shards as instanced quads with additive blending, colours from the theme. "Physics-based" to the owner means weight: speed builds downhill, bleeds uphill, the camera leans.
2. Verify in motion (not yet seen by anyone but the owner): Tunnel motes wall after the last tweak, pattern front arriving, Wormhole bends, Illusions fades.
3. Illusions extras he liked: wireframe lines on the sphere, motion blur on near points, more surfaces. Reuse the point cloud for Wormhole patterns.
4. Apply the eased spectrum to skyscrapers (5.3).
5. Daylight is tuned for City only.
6. Never built: black hole world (12-ring disc = bands, beats fall in, jets on drops), ferrofluid.

## 8. Things not to do

- Do not list the owner's GitHub repositories; use only `amit2279/soundscape`.
- Do not re-enable Temple, Mandala, Runner, the twisted-lines illusion or Wormhole type 1 unless asked.
- Do not make illusions change by themselves.
- Do not tie free-roam speed to the music.

## 9. Coaster lab: full specification (state on 2026-11-14)

File `coaster-lab.html`, about 300 lines, standalone. Artifact "Coaster lab", slug `c68270d2-057b-4b14-83d6-67b9296d41d3`. The owner rides it and loves it ("vertigo-inducing"); it is the benchmark. When he says so, port it into `index.html` in place of `coastPlan`/`coastStep`/`coastCam`.

### 9.1 Principles the owner has set
- It must feel like a real coaster: speed changes come from the track, never from the music directly.
- Drops must bite. Gravity is deliberately stronger than real (`G=14`).
- Objects only on big musical moments, and all solid 3D. No flat shapes. Nothing cluttered.
- The view must feel close: camera low on the rails, moderate lens.
- No mouse look in the lab.
- Effects live inside closed tunnels and are hidden until you are in them.
- Fireworks are off for now (too close, too frequent). If they return: beside the track, rare.

### 9.2 Audio
`synthDemo()` makes a 95 s demo (quiet, build, full, twice). `analyse()` gives per-frame (60 fps) energy `E`, bass `B`, smoothed intensity `inten`, `beats` (`{t,s}` from bass onsets) and `drops` (largest rise of 4 s mean energy, at least 20 s apart, snapped to the nearest strong beat). When porting, use the main app's `A.beats`, `A.drops`, `A.inten`, `A.bass` instead.

### 9.3 Track generation: `buildRide(A)`
State: position, yaw, pitch, bank, speed `v`, time `t`. One `step(kp, ky, mode)` advances `DS=0.4` m:
- pitch and yaw curvature requests are low-pass filtered over about 4.5 m and 7 m (this is what removes jerk);
- bank eases toward `atan(v²·ky/G)·0.95`, so lateral force goes down through the seat;
- speed: `free` mode uses energy, `v² += 2·(−G·sin(pitch) − (0.012·G + 0.00016·v²))·DS`, floor 2.5 m/s; `chain` eases to the chain speed; `brake` decelerates at 7 m/s² to the chain speed; `boost` accelerates at 9 m/s²;
- `t += DS/v`; normal force `GN` is stored for the readout and camera.
Samples are stored per step: `X Y Z YAW PIT ROL V T GN`.

Elements (all sized from the speed the train has at that point):
- `toPitch(target, Gt)`: curve until the pitch is reached, curvature from `kFor` = `(Gt − cos(pitch))·G/v²`, minimum radius 9 m, maximum 70 m.
- `hill(th)`: pull up at 3.5 g, float over at 0.02 g, pull out at 3.6 g.
- `turn(angle, gLat, side)`: yaw curvature `gLat·G/v²`, radius at least 13 m; a 450-degree version with a slight descent is the helix.
- `loop()`: full circle of pitch with target g `2.9 + 1.8·cos(pitch)`, radius between 7 and 45 m: tight at the slow top, wide at the fast bottom (a teardrop).
- `corkscrew()`: roll through 360 degrees over `clamp(2.3·v, 38, 85)` m, smoothstep eased.
- `boost(vt)`: only if speed falls under 11 m/s.
- `liftAndDrop(td)`: level out, brake to chain speed, climb at 35 degrees (`0.61` rad) for height `H = clamp((time available − 4)·6.5, 26, 92)` m, round the crest at 0.12 g, fall at 73 to 82 degrees, pull out at 4 g where the pull-out arc reaches the base height. **Sync**: the whole lift is rebuilt up to five times, each time correcting chain speed by `Tc/(Tc − error)`, until the moment pitch passes −30 degrees is within 0.03 s of the song's drop.
- `pick()` chooses the filler between lifts from intensity and speed: loop (fast, loud, at most one per 14 s), corkscrew (loud), hill (never two in a row), otherwise a turn or helix, alternating sides.
Order: 8 m of straight, then for each drop fill until 15 s before it and call `liftAndDrop`, then fill to the end.
Demo numbers: 1,426 m, 138 km/h, +4.4 g, −0.6 g, both drops within 0.02 s.

**Angle continuity (bug fixed 2026-11-14):** `loop()` and `corkscrew()` reset pitch and roll by 2π when they finish. Stored raw, that is a jump between two neighbouring samples, and `frameAt` interpolating across it swung the camera through a full turn for one sample (the owner saw the rails flash across the screen). `buildRide` now unwraps `PIT`, `ROL` and `YAW` before storing. Keep this when porting.

`idxAt(R,t)` is a binary search from song time to sample index; `frameAt(R,f,pos,d,u,r)` interpolates the frame (roll applied).

### 9.4 Track model: `buildWorld(R)`
- `sweep(R, offsets, every, radial)` sweeps tubes along the track; each offset is `[right, up, radius]`.
- Two rails at ±0.62 m, radius 0.085, dark.
- Two spines at ±0.2 m, 0.52 m below, radius 0.125, dark.
- Eight neon line tubes: two on each rail, two on each spine. Material `trackMat(colour, emissive, run, neon)`; with `neon` the colour flows along the track by distance and time, brightness follows the beat and bass, and a pulse runs away along the lines with the bass.
- Connector every 2.4 m: one smooth half-ellipse-like curve from under one rail, beneath both spines, up to the other rail, built from 14 short instanced boxes, magenta. No bar above the rails, no straight struts, no pillars.

### 9.5 What you pass
All use `objMat` with per-instance `aI = (song time, hue, seed/phase, mode)`; instances more than 30 s of song away are culled in the vertex shader.
- **Gates** (mode 0): `TorusGeometry` with 3, 4, 6 or 40 segments (triangle, square, hexagon, ring), stretched 4x along the track so they are deep frames. Placed in **series**: 10 down each drop from 0.2 s after it at 0.26 s spacing, and 5 at 0.11 s spacing on each of the strongest accents (the top `dur/7` beats, at least 4 s apart, not near a lift). Size grows slightly down a series.
- **Rotation with inertia**: `spinV` rests at 0.4 rad/s; every beat adds `2.6·strength`; friction returns it at rate 0.8; capped at 7. `uSpA` is the integrated angle; `uSpB` and `uSpC` each trail the one before (rate 3.5). A gate's angle blends A→B→C by its place in the series, so the surge travels down the line. Direction alternates by series.
- **Glow**: gates brighten with beat and bass, flare as you approach, and dim inside 7 m so they never flood the screen.
- **Solids** (mode 1): icosahedron, octahedron, dodecahedron, torus knot, 8 to 25 m from the track, kept clear of every part of the track (`clear`) and never beside a tunnel; they tumble and swell with the bass.

### 9.6 Closed tunnels
- Stretches: every 12 s or more of song, 8 s long (`TUNLEN`), never from 13 s before a drop to 5 s after it. Demo: five.
- **Clearance rule (fix for black patches the owner saw):** a stretch is used only if every point of it is at least 14 m from all non-adjacent track (`tubeClear`). Without this an opaque tunnel wall cut across the rails elsewhere on the ride, or two tunnels intersected. The motes style also turns slowly round the tube (`u + 0.012·time`, cell ids wrapped mod 26 to keep the seam invisible).
- Geometry: a tube of radius 6.5 m centred 0.6 m above the rails, one ring every 1.2 m, 28 segments. **The ring is built from the track frame with the roll removed**, so the wall does not bank with the train: when the train banks or corkscrews, the pattern turns round the rider. `aUV` = (angle 0..1, metres along), `aE` = 0..1 along the tunnel.
- Material `tunMat(style)`: **opaque**, double-sided. Uniform `uIn` eases to 1 while song time is inside the tunnel (from 0.12 s before the mouth) and back to 0 after. Output is `mix(shell, pattern, uIn)`: from outside or before entry it is a near-black tube with faint hoops every 5 m; inside it shows the pattern. Because it is opaque it hides the stars, the far track and the gates beyond it.
- Styles cycle 0 to 3: glowing motes, spiral bands, liquid contours, fine particle dust. All use whole-number repeats round the tube so there is no seam. Brightness follows beat and bass.
- **Update:** the wall is now smoked acrylic, not opaque: `transparent`, `depthWrite:false`, alpha 0.7 where dark rising to 1 where the projected pattern is bright. And **no gates are placed inside a tunnel** (accent series skip tunnel stretches): the owner's rule is either a tunnel or shapes, never both.
- **Update 3: the acrylic transparency was reverted.** Walls are fully opaque again (the owner disliked seeing other tunnels and track through them). Do not make them translucent.
- **Update 2:** the pattern now runs all the time on the inner face of the wall (inner face = `dot(aN, uCam − position) < 0`, with `aN` the outward ring normal), at 60% brightness, easing to 100% via `uIn` as the rider enters. The outer face stays the dark shell. So you see the tunnel already animated through its mouth, and faintly through the acrylic, instead of it switching on.
- The old open particle field (`fieldMat`) is no longer placed; its material is still defined.

**Tunnel glow (owner's last tuning, he called the result perfect):** the music-driven part of the wall brightness was doubled: `lit = pattern·(0.35 + 1.8·uBeat + 0.9·uBass)`, mote halo `0.3 + 3.2·uBeat`, dust flash `3·uBeat`. `uBeat` is the strength of the latest beat times `exp(−7·age)`, so each flash starts decaying at once. He declined rebuilding the textures from particles.

### 9.6b Fireworks (re-enabled 2026-11-14, new rules)
`FIREWORKS=true`. Chrysanthemum bursts beside the track, never on it: centre is (after the owner asked for them closer) 4 to 9 m to one side and 7 to 11 m above where the train will be 1.3 s after the beat, exploding on the beat, so the rider passes it and leaves it behind while it decays (life 4.6 s). At least eight bars between events (beat period = median beat interval; gap = 32 beats). Sides alternate. Every third event is three bursts on three consecutive beats on alternating sides. None while in a tunnel. Demo: about five events in 95 s.

**Connector colour:** connectors use `trackMat(..., hue=1)` and drift together slowly through the palette. In the main app, tie this to the theme colours (`uA`/`uB`) instead.

### 9.6c Added 2026-11-14 (unreviewed by the owner at the time of writing)
- **Speed streaks** (`streaks`): 420 line segments fixed in a 40 m repeating lattice round the camera; the second vertex of each is pushed along the velocity by up to 5.5 m; they fade in between 16 and 38 m/s.
- **Swarm is switched off** (`m.visible=false` where it is created): the owner said it was not working. The streaks, sea and soft tunnel mouths he approved ("madness").
- **Swarm** (`swarm`): 2,600 points in a flock whose centre (`uSwC`, eased) sits 1 s ahead on the track and weaves ±9 m sideways and 0 to 7.5 m up; each point follows its own sine paths in the track frame; the flock contracts 45% on each beat; it fades out in tunnels and for part of the time (`uSwOn`).
- **Sea** (`sea`): a 5 km plane 8 m below the lowest track point (so no tunnel dips into it), following the camera in x and z. Shader: dark swell, glittering plankton cells, a wake glow that grows as the camera gets lower, and up to six rings (`uRip`: x, z, song time) dropped under the train on strong beats and spreading at 26 m/s.
- **Tunnel mouths**: wall material is `transparent` again only so alpha can fade over the first and last 11% of the length; the body stays alpha 1 (opaque). Do not lower the body alpha.

### 9.6d Changes of 2026-11-14 (afternoon)
- **Sea rings removed** (owner disliked the blurred green circles). The sea keeps its glitter and a faint wake; the `uRip` loop is still computed but no longer adds light.
- **More gates, closer together, five shapes**: triangle, square, pentagon, hexagon, ring (torus segments 3, 4, 5, 6, 40). 18 per drop at 0.17 s spacing; a series of 9 at 0.1 s spacing on any beat stronger than 0.3, at least 2.6 s apart, outside 6.5 s before to 3.6 s after a drop, still never in or near a tunnel or a lift.
- **Lens**: field of view is now `56 + 10·min(1, v/50)`. **Bug found**: since the "longer lens" change, a `//` comment had cut off the statement that applies the field of view, so the camera had been stuck at its initial 72 degrees. Fixed (comment is now `/* */`). This is the same trap as in section 3.

### 9.7 Rider camera (in `frame`)
- Position: 0.6 m above the track centre, moved down by `0.04·(g − 1)` (clamped), plus a rattle of amplitude `0.022·(v/40)²`.
- Direction: 62% the current track direction, 38% the direction `clamp(0.35·v, 3, 14)` m ahead, tilted slightly down; up vector is the track's up. The quaternion is slerped toward this at rate 9, which is the head lag.
- Field of view `70 + 16·min(1, v/50)` degrees, eased. Do not go wider: the owner sees wide lenses as "far".
- Bloom strength 0.62, radius 0.5, threshold 0.3.

### 9.8 Readout and controls
Top left: speed, force, height, "chain lift", countdown to the next drop. Bottom: play/pause, seek, time, upload. Space toggles play. Test hooks: `window.__lab = {report, objects, ride, seek, play, pause}`; `ride.fx.tunnels` lists tunnel start times.

### 9.9 Ideas the owner has raised but not approved or built
Motion blur and speed streaks; chain and wind sound; fireworks placed beside the track; tunnels with more wall styles (the Wormhole patterns); deliberately putting corkscrews inside tunnels to show off the turning walls.
