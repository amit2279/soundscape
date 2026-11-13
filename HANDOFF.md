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
0b. **`coaster-lab.html` (2026-11-14): the physics rebuild, as a separate test page.** The owner found the in-app Coaster unnatural, so the next version is being tuned here before it is ported into `index.html` to replace `coastPlan`. Standalone file, own small analysis and demo synth. `buildRide(A)` lays the track out in space in 0.4 m steps: speed from energy with drag; curvature from target g at the current speed (`kFor`), smoothed over a few metres; elements `hill`, `turn`, `loop` (teardrop), `corkscrew`, `boost`, `liftAndDrop`. `liftAndDrop(td)` solves the chain speed by fixed-point iteration so the crest (pitch passing -30 degrees) lands on the song's drop. Report on the demo: 1,444 m, 121 km/h, +4.4 g / -0.6 g, drops within 0.11 s. Track is two tube rails, a spine, three-piece ties every 1.2 m, support columns. Objects only on big moments: six torus gates per drop, one gate per top accent, a few solids kept clear of the track. Rider camera: looks ahead, head lag, g-force seat offset, speed rattle, no mouse look. Published as its own artifact "Coaster lab" (slug `c68270d2-057b-4b14-83d6-67b9296d41d3`). Second pass after owner feedback: gravity constant raised to 14 (he wants drops to bite), lifts up to 92 m, pillars removed, rails are dark tubes with thin neon line tubes along both rails and the spine (colour flows along the track), connectors are an open yoke frame of six boxes every 2.4 m, gates are tori stretched 4x along the track and placed in series (10 per drop, 5 per top accent) with rotation and scale delayed per gate (`aI.z` is the phase), camera lowered to 0.6 m with a wider lens and a slight downward look so the track fills the frame. Owner called the first pass "genius"; second pass awaiting his feedback. Still to do: motion blur, sound, then port into `index.html`.
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
