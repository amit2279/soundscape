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

## 8b. The lab coaster is now in the main app (2026-11-14)

`index.html` section "Coaster" was replaced by a port of `coaster-lab.html`, generated by a script that copies three text ranges of the lab file (ride generator, materials and world builder, streaks/swarm/sea) into one closure `COASTER=((MU,scene,camera)=>{...})(U,scene,camera)` and adds `step(dt,t,on,playing,pxH)` and `cam()`. Wrappers `coastStep` and `coastCam` keep the old call sites. Differences from the lab:
- uses the main analysis: `{fps,F,dur,inten,B:A.bass,beats,drops}`; drops within 7 s of the start or 8 s of the end are ignored; if a song has none, one is placed at a third of its length;
- its own uniform object inside the closure (named `U` there, shadowing the main one); only `uA` and `uB` are shared, and the connectors use them, so they follow the theme;
- no readout, no lab stars (the main void sky is used), no mouse look;
- camera near plane is switched to 0.1 while the Coaster is on and back to 1 after (the rider is 0.6 m above the rails);
- field of view goes through the main `fovOver`;
- the ride is rebuilt when the song changes (`curA!==A`).
Demo track in the main app: 2,078 m, 152 km/h, +4.9 g, three drops within 0.06 s, eight loop/corkscrew angle wraps handled, 135 gates, three tunnels.
**Workflow from here:** keep experimenting in `coaster-lab.html`; to bring changes over, re-run the port (the script is in section history of the session; it is simple enough to rewrite: slice from `let RIDE=null;` to the rendering marker, from `const U={uVel:` to `const stars=`, from `/* speed streaks:` to `const composer=`).

## 8c. Coaster track v2 (lab only, 2026-11-14)

`coaster-lab.html` now has two track layouts. Button "Track v1/v2" in the bar, or key V, rebuilds the ride in place (`setVer`). `buildRide(A,ver)`; v1 is untouched and is what the main app has. v2 adds:
1. **Lower thresholds.** Loops and dive loops no longer wait for a fast stretch; they are given the entry speed they need (`boost` to 27 / 26 m/s). Loops may repeat after 8 s (was 14).
2. **Chains.** After every main drop `chain(tn)` runs 2 or 3 inversions back to back while at least 19 s remain before the next event.
3. **New elements:** `loop2` (double loop), `zeroG` (zero-g roll: a weightless hill with one full roll), `overbank` (climbing turn leaned about 100 degrees), `dive` (half roll up, half loop down, leaves the way it came), `topHat` (launch to 36 m/s, 60 degree climb, weightless crest).
4. **Launches.** `launchOnBeat` coasts to the next strong beat (s>0.45 within 3.2 s) and accelerates at 17 m/s² ('launch' mode in `step`), then a top hat or double loop. At most one per 12 s, only with 18 s clear before the next drop.
5. **Music character.** `choose()` compares intensity and bass with their medians over the song: heavy and loud gives loops/double loops/dive loops; loud but light gives corkscrews/zero-g rolls; quiet gives overbanked turns and hills. No element twice in a row.
6. **Small drops.** Up to 8 secondary peaks (largest 3 s rises in intensity, at least 16 s from a main drop and 18 s apart) get `liftAndDrop(td,0.45)`: a lift under half height and a shallower drop. Marked `mini:true` in `R.marks`.
Other v2 details: the lift solver brackets the chain speed (the old update oscillated when braking came first) and lowers the lift by 22% at a time if the chain flat out is still late; `R.els` lists `[sampleIndex,name]` and the readout shows the current element; `R.CUT` marks the one sample after a dive loop where yaw/pitch/roll are rewritten by half a turn, and `frameAt` does not blend angles across it (the angle unwrap skips it too). **If v2 is ported to the main app, `frameAt` and `CUT` must come with it.**
Checked headless on the demo only: four drops within 0.01 s, no crawling outside the lifts, +4.9/−0.9 g, still frames through a dive loop look continuous. Launch and top hat were exercised only in a forced test build. Not checked: any real song, motion at full frame rate, whether new elements cross other track (nothing prevents that in v1 either).

## 8d. v2 second pass after owner feedback (2026-11-14)

Owner loved the v2 path and the track winding through itself (keep that). Changes, all v2 only unless noted:
- **Lift and drop feel:** braking into the lift is gentle when there is time (`bd`, 3.4 to 11 m/s²), the chain takes the car over about 9 m instead of 3, lifts start up to 19 s before a main drop, the crest radius is at least 17 m (was 9), main drops are 81 to 87 degrees, and the fall uses 1.4 times gravity (`'fall'` mode, `GF`) so it is heavier than physics. Peak about 183 km/h on the demo.
- **Bigger inversions:** loops enter at 34 m/s with softer g (`loop(2.5,1.6,1/11)`), new `giant loop` (launch to 43 m/s), turns and helices no tighter than 21 m radius (`TK`), corkscrews 60 to 115 m long.
- **Lulls:** `cruise` (wide, level, speed easing down to 17 m/s) when intensity is under 85% of the song's median. After a main drop the chain is inversion, `helix` (3.8 g), inversion.
- **Balance:** small drops get 8 gates (was 18); beat gate runs at least 5 s apart (2.6 in v1). v2 tunnels are 6 s long (8 in v1), at least 10 s apart, blocked from 6.5 s before a lift starts until 3.4 s after the drop, and need only 9 m from bare track (14 m from another tunnel or their own tube). On the 95 s demo this gives 2 tunnels and about 90 gates against v1's 5 and 90: the demo has four drops in 95 s and loops cannot be inside a tunnel (the tube would cut itself), so there is little room. **Open:** check the balance on real songs; if tunnels are still rare, let the generator plan a `cruise` stretch on purpose and put the tunnel there.
- **Both versions:** gates and solids that would reach into any tunnel's tube are left out (`inTube`), and a tunnel may not fold back into its own tube (`tubeClear` now checks its own samples more than 36 m away along the track). This was the owner's "other track's shapes visible inside the tunnel" and probably his "black texture" patches; the second is not confirmed.

## 8e. v2 third pass (2026-11-14)

- **Drop timing (v2):** the lift solver now times the moment the train reaches 80% of the drop's steepness in `'fall'` mode, not the tip-over at 30 degrees. On the demo the train is at about 67 degrees down and 85 km/h on a main drop's beat. `m.at` in `R.marks` is that moment.
- **No riding through track (v2):** `safe(fn)` lays a piece, and if any new sample is within 4 m of track more than 44 m back (`hits`), takes it back (`snap`/`back`), adds a small sideways turn and lays it again, up to three times. Used for every element, chain and lift. Loops swing their upper half sideways (yaw 0.016/m while cos(pitch)<0.5) and the dive loop yaws while rolling, because their own exit used to pass through their own entry. `R.report.rerouted`, `.crossings`, `.crossAt` say what happened; demo: 1 rerouted, 0 left.
- **Fireworks (both versions):** at least six bars apart (was eight).

## 8f. Evening of 2026-11-14

**Coaster lab**
- **Ride it yourself.** With the song stopped (or over), the up arrow or W is the motor: `free` object, thrust eases to 16 m/s² while held and cuts when released, gravity along the track (`G*sin(pitch)`) and drag always act, down arrow or S brakes, the car can roll back. Position is `free.f` (sample index); the "song time" every effect uses is read back from the track at that position (`R.T`), so gates, tunnels and fireworks still happen where they belong. Off the far end returns to the start. No sound in this mode. Play, seek or V leaves it. Owner asked for a closed circuit later (not built).
- **Fireworks:** events at least six bars apart; `nRun = max(3, events/4)` of them, spread evenly, are runs of two or three on consecutive beats (`R.fxRuns`).
- **Tunnel outside:** the outer face is a skin of glowing particles that flare on the beat (in `tunMat`, `shell`), instead of near-black.
- **Beat-in (v2):** `beatIn` = first place with four strong beats (s>0.45) inside 2.6 s. Drops earlier than 1 s before it are discarded; if the song has no drop within 8 s of it and it is later than 9 s, it becomes a main drop. In `R.report.beatIn`.
- **Depth of field:** `renderDepth()` draws the scene again at half size with `depthMat` (distance/260 m; points, lines, streaks, sea and swarm hidden), and the last pass `dof` blurs up to 1.8 px with distance. Key B switches it off. Not measured on a real GPU; if it costs frames, remove `renderDepth()` and the pass.

**Main app**
- **Playlist:** the file input is `multiple`; `PL={q,i}`, `plAdd(files)` (ten at most, also from drag and drop), `plGo(i)`, `finish()` goes on to the next song, `,` and `.` or the arrows under the song name step through. Loading the demo clears it. Files never leave the browser.
- Still on coaster v1. Porting v2 needs: `buildRide(A,2)`, `frameAt` with `CUT`, the `buildWorld` changes, and the bass array as `B`.

**SoundCloud: not built.** It needs the owner to register an app at SoundCloud (client id and secret) and a small server function (Vercel) that keeps the secret, gets the token, resolves a pasted track or playlist link and proxies the audio stream so the browser may decode it (cross-origin). Check SoundCloud's API terms first.

## 8g. Song length limit (2026-11-14)

A one-hour mix took for ever because the whole song is decoded and analysed before the ride. Main app: `MAX_MIN=12`; `probeDur(file)` reads the length from the file header through an `<audio>` element before decoding (falls back to refusing files over 150 MB when the header gives nothing, and to a check after decoding); too long gives a toast, and in a playlist the song is skipped. Lab: refused after decoding if over 12 minutes. **Open, if long mixes matter:** analyse in chunks in a worker and build the coaster a section at a time (drops are found over the whole song today, so the coaster needs the most work; the reactive worlds only need the analysis to stay ahead of the playhead).

## 8h. Lab: sounds, instruments, reverse, particle tunnels (2026-11-14 night)

- **Reverse:** in self-drive the down arrow or S is the same motor backwards (brakes, then reverses to 45 m/s). Either key starts self-drive.
- **Ride sounds** (`SFX`, `sfxInit`, `sfxStep`, `blip`, `tone`; all synthesised, key M mutes): wind (band-passed noise, level with speed squared), wheel rumble (low-passed noise), a double click at a rail joint every 7 m, a chain tick every 0.55 m on a lift (song mode only), a panned swoosh for every gate passed (`R.pass`, the gates' times, crossed in either direction), a falling boom at each drop (`m.at`), an air thump at tunnel mouths. Plays in song mode and self-drive. **Not heard by the builder: levels are guesses and need the owner's ear.**
- **Instruments** (self-drive only): `#gauge` speed dial with motor bar and g, `#map` heading-up map of the track within about 210 m, brighter near the rider's height, drops marked. Original design; the owner's references were a racing game and a car cluster, for the idea only.
- **Tunnels:** walls are fully opaque (`transparent:false`, mouths cut clean at 2.5% of the length). Styles 0 and 3 are now layers of randomly placed glowing particles (`sparkR`) that turn around the rider at different speeds; the glow fades before its patch edge so no square shows.

## 8i. Lab: glow, bioluminescent tunnel, map always on (2026-11-14 late)

- **Glow:** bloom is now 0.8 strength, 0.82 radius, 0.34 threshold (was 0.62/0.5/0.3): a wider, softer halo on everything lit. 1.15/0.9/0.16 was tried and floods the screen.
- **Bioluminescent tunnel:** `tunMat` style 4: long blue streaks drifting along the wall, finer ones between, a faint blue haze. Every third tunnel starting with the second (`k%3===1`); the others cycle styles 0 to 3. While the rider is inside one, `U.uBio` eases to 1 and `trackMat` turns rails and connectors blue; it eases back outside. **The owner was clear: this is an occasional accent. The coaster stays colourful and psychedelic. Do not spread the blue.**
- **Map** is shown for the whole ride; the speed dial only in self-drive.
- **Not built:** closing the track into a circuit (owner said it is fine to leave).
- Seen while testing, not new: paused inside a run of round gates, the nearest ones fill the screen with their colour.

## 8j. Blue moments (2026-11-14 late)

The owner saw a test frame where the whole ride was blue with heavy glow and asked for that look a few times per ride. `R.bio` is a list of windows `[td-0.6, td+9.5]` at every second big drop starting with the first (a second one at 62% of the song if there would be only one). In a window, or inside a bioluminescent tunnel, `U.uBio` eases to 1: rails and connectors (`trackMat`) and gates and solids (`objMat`) turn blue and cyan, and bloom opens from 0.8/0.82/0.34 to 1.15/0.9/0.16; all ease back after. Ordinary tunnel walls keep their own colours. Still an accent: the rest of the ride stays colourful.

## 8k. Lab coaster v2 merged into the main app (2026-11-14, 23:30)

`index.html` now has track v2 and everything from sections 8c to 8j except depth of field, the lab's stars, its text readout and the v1/v2 switch.
- **How:** `tools/port_coaster.py coaster-lab.html index.html` regenerates the whole Coaster section from the lab (four text ranges plus a `step` written for the main app). **Change the lab, run the script; do not hand-edit the copied parts in `index.html`.**
- **Wiring:** play bar, seek and song loading are the main app's. `coastStep` passes `drive` from the app's `keys` (up/W = +1, down/S = -1) and whether the song has ended. Self-drive starts when a drive key is held while the song is paused or over, and stops when the song plays. The on-screen keypad is shown in the Coaster too.
- **Glow:** while the Coaster is on, `coastStep` sets the app's bloom to 0.8/0.82/0.34 (times the theme's glow), opening to 1.15/0.9/0.16 in a blue moment; leaving the Coaster restores radius 0.55 and threshold 0.86.
- **Instruments:** `#cMap` (top left, whole ride) and `#cGauge` (bottom right, self-drive only), class `cinst`, hidden with the rest of the interface (`nohud`).
- **Sounds** use the app's audio context and go straight to its output (not through the volume slider). No mute key in the main app yet.
- **Generator fix made during the merge:** the lead before a lift grows with speed (`+0.15 s per m/s above 28`), which fixed a drop that was 2.2 s late on the main demo.
- Checked headless on the main demo: four drops within 0.01 s, no crossings, blue moment, bioluminescent tunnel, self-drive with dial, switching back to City restores it. Not checked: real songs, motion, sound.

## 8l. Toolbar rework, step 1 (2026-11-14, 23:45)

The owner is reworking the top bar one step at a time. Done: every mode tab has its own thin line icon beside its name (`WI` map, inserted at startup next to where Planet is created; icons only under 1040 px width). Planet is out of the tab bar, in its own group `#planetSeg` beside Go Nitro; **where Planet and Go Nitro finally live is undecided, the owner will say.** His references for the icons were outlined category chips (icon plus label, thin strokes); ours are original glyphs. Next from him: which mode and option combinations do not work together.

## 8m. Toolbar rework, step 2 (2026-11-15)

- **Abyss and Illusions are hidden** (CSS on their tabs, removed from `WORLDS`, so T and shuffle skip them). The code is intact; restore by removing the CSS rule and adding them back to `WORLDS`.
- **Planet** shows only where it exists (`PLANET_OK`: city, terrain); **Go Nitro** only where it does something (`NITRO_OK`: city, terrain, worm, tun). `setWorld` toggles class `gone` (drops in, lifts away), leaves Planet view when switching to a mode without it, and `togglePlanet` refuses there.
- **What works where** (from a 30-frame contact sheet, `test/matrix.png` in the build folder, plus the code):

| | City | Terrain | Wormhole | Tunnel | Coaster | Loom |
|---|---|---|---|---|---|---|
| Cruise / Fly / Skyline | 3 views | 3 views | no effect | no effect | no effect | 3 distances |
| Planet | yes | yes | no | no | no | camera only, hidden |
| Go Nitro | yes | yes | faster | faster | no | no |
| Kaleidoscope | yes | yes | yes | yes | yes | yes |
| Drive yourself | yes | yes | no | no | yes (on rails) | no |
| Scroll zoom | yes | yes | no | no | no | yes |

- **Step 3 (done):** Go Nitro is now called **Amplify** (same bolt icon; the code still says `nitro`). Planet's icon is a turning wireframe globe (CSS, class `globe`). The camera switch `#camSeg` hides in Wormhole, Tunnel and Coaster (`CAM_OK`). The mode bar is frosted white (0.86).
- **Open, owner deciding:** the final place for Planet and Amplify. Suggested to him: Planet beside the camera views in the bottom bar (it is a fourth view), Amplify at the top of the right-hand effects column (it is an effect). Daylight was not tested outside the City.

## 8n. Small things, 2026-11-15 early

- **Landing flight** fades through black where it restarts (every 360/7 s): `attK`, a black div right after the canvas, under the interface.
- **Planet icon** is a still wireframe globe (the owner did not want it animated).
- **Black out theme** (`THEMES.lights`, flag `lights:1`): black sky, fog and walls, plus `dkPass`, a pass straight after the scene render that multiplies each pixel by `smoothstep(.2,.5,brightest channel)`, eased in by `darkT`. Only lit things survive, and bloom comes after it so they keep their halos. Needs the composer (Quality 3 or higher); below that it is just the black colours. The older "Blackout neon" theme is unchanged.

## 8o. Per-mode visibility, part 2 (2026-11-15)

- **The Coaster is always in open space. Never a horizon, whatever the colours** (owner, firmly). Three causes fixed: its sea was an opaque plane with a far edge (now additive, light only, faded out by 420 m; lab and main); the void sky took the theme's sky colour (`uTintV` is 0 in the Coaster); the Mono light theme's invert filter (cancelled for the Coaster in CSS).
- **Colours are hidden in the Coaster** (`.swwrap`). The connectors still take whatever theme was last chosen elsewhere.
- **Effect toggles fold away where they do nothing** (`fxVis()`, called from `setWorld`, `setMode`, `setKal`): fireworks only in City and Terrain; solar system only in Planet view; crystal facets and light rays only on the kaleidoscope planet; the two kaleidoscope switches everywhere.
- **Keys in the Coaster:** only up and down are shown.

## 8p. Black hole lab (2026-11-15), a new mode in the making

`blackhole-lab.html`, its own test page like the coaster lab; not in the main app yet. The owner wants it as **its own mode**, not a Planet variant.
- **Look (owner's rules):** a black ball in empty space with **no rim, no ring, no glow of its own**; it is revealed only by the lasers. 2,600 beams (`NBEAM`), one instanced strip each, turned to face the camera, starting on the surface and pointing straight out, each with a bright point at its tip. The ball hides the far-side beams; beams aimed at the camera are dimmed 93% so the middle stays a black disc. A beam passing within 12 units of the camera fades. Additive, bloom 0.85/0.8/0.18.
- **Sound, finer than the main app:** `analyse` makes **48 log-spaced bands** (40 Hz to 16 kHz, FFT 2048, hop 1024, about 43 readings a second), and for each band a level track and an **onset track** (positive change), each normalised by that band's own loud moments so quiet sounds count. Each beam belongs to one band (`aInf.x`) and has a firing threshold (`aInf.y`): the harder the onset, the more of that band's beams fire. `uLev` (level, eased at 10/s) gives a breathing stub; `uShot` (onset, eased out at 26/s and home at 2.6/s) gives the long shot. Low bands throw fat beams with the bass. `A.hits` (whole-spectrum jumps) fire everything a little (`uAll`) and lean the camera in.
- **Controls:** drag to orbit, scroll to zoom, C or the button cycles six colour pairs (ember, blood, ice, acid, violet, white).
- **The owner asked whether effects can follow the small sounds in psytrance and similar.** This per-band onset analysis is the answer and is meant to go into the main app's analysis later (it has 12 bands and whole-song beats only). Further steps discussed: pitch sweeps (a band's energy moving up or down the spectrum), and repeating-pattern detection.
- Checked headless on the demo, stills only. Not checked: real songs, motion, frame rate with 2,600 beams on a real GPU.

## 8q. Black hole lab, second pass (2026-11-15 morning)

Owner's corrections, all firm:
- **One colour only, and never white.** "Bright" means a strong, saturated laser of the active colour with a glow of the same colour. Nothing is mixed towards white in any shader; palettes are a hue and its near neighbour (default `red` = pure 1,0,0); a last pass divides any over-bright pixel by its brightest channel, so piled-up light keeps its hue. A whited-out test frame was rejected outright.
- **A bright origin point on the surface** where each beam leaves (a `THREE.Points` pass sharing the beams' attributes), not a point at the tip.
- **Front lasers hit your face:** an origin point whose beam is firing and aimed within a narrow cone of the camera (`pow(face,26)`) grows and throws a four-way flare.
- **Sparse enough to follow each beam:** the firing threshold is `0.6 + 3*aInf.y`, so a soft sound fires a few beams and a hard one a few hundred of the 2,600, never all. Beams aimed at the camera are no longer dimmed.
- Bloom 0.95/0.9/0.12.

## 8r. Black hole lab, third pass: measured from the owner's reference (2026-11-15)

The owner withdrew "red only" after looking closer at his reference; seven beams were sampled from it:
- **Source point:** pale warm pink, about rgb(255,180,175), saturation 0.25 to 0.33, full brightness, **no wider than the beam**.
- **8% along:** salmon, saturation about 0.5 to 0.6, hue 0 to 7 degrees.
- **Half way to the end:** deep crimson, about rgb(240,35,70), hue about 350, saturation 0.8 to 0.9.
- So hue moves about 15 degrees (warm red to crimson) and saturation climbs from 0.3 to 0.9, most of it in the first quarter; brightness stays within 0.9 to 1.0.
In the lab: palette entry A is the colour at the surface, B the colour further out (`smoothstep(0,.55,along)`). The core is paled towards white by `0.6*exp(-4.2*along)`, so the source is pale and hot as in the reference. **This measured version is the one the owner settled on** (he tried a saturated, no-white source that tapers with distance, commit fa1011f, and asked for this one back). Source points are 0.15 to 0.22 units (the beam's width), paler and brighter, and only a face-on hit grows them. A **Glow slider** (0 to 3, default 1.35) sets bloom strength so the owner can find his value. The hue-keeping pass stays. Smoke that the beams light up is the next thing he wants, after "some cool changes" he has not described yet.

## 8s. Black hole lab: rest state (2026-11-15)

With no music playing (`uRest` eases to 1), source points light up at random and fade again with **no beams**: each point has its own slow clock (`uTime*0.3`), and on about one tick in seven it rises and falls as `sin²`. The beams and points now sit in a group `hole` that always turns (0.11 rad/s about Y with a slow nod), so the shaders work in the group's frame: they use `modelViewMatrix`, and `uCam` is the camera position in the group's space.

## 8t. Black hole lab: smoke, beat pulse, random colours (2026-11-15)

- **Smoke:** 3,200 soft noisy puffs (`THREE.Points`), each tied to one beam, drifting slowly out along it, spreading and thinning. `uSmoke[band]` follows `uShot` up at 2.4/s and down at 0.3/s, so the amount follows how hard the lasers fired and then hangs and decays. A puff shows only if its beam has been firing (`had`) and is about six times brighter while that beam is firing now (`lit`): the laser lights its own smoke. Same colour as the beam. Additive, so it is glowing haze; dark smoke cannot show on black.
- **Beat pulse:** a kick (strongest onset in the six lowest bands above 0.62, at most one per 0.18 s) sets `pulseT`; the hole's scale eases up to 1.1 and straight back. No scaling between beats.
- **Random colours:** last entry of the colour button; `uRand` eases to 1 and every beam, source point and puff takes its own hue (`h2rgb(aInf.w)`). Many hues piled up add to white, so this mode first ran at half strength; the owner found it light, and it now runs at 85% (smoke at 65%) with coloured sources.
- **Smoke stays at the surface** (owner: the surface is hot where the lasers leave it): puffs rise only to 1.44 radii, are smaller, and are dimmed 75% on the face turned to the camera so the centre of the hole stays dark. A stronger first try turned the whole disc red and was rejected by the builder before publishing.
- **Drag feels heavy:** half the turn per pixel (0.0025 and 0.002 rad/px), and the camera follows at 2.67/s instead of 4/s, so it takes half as long again to settle.
- Checked on stills. Not checked in motion: the smoke's drift, the pulse's feel, the drag.

## 8u. Black hole lab: stars (2026-11-15), a trial

3,500 faint stars 900 to 1,600 units out, tinted 30% towards the laser colour, turning very slowly; button "Stars" or key S switches them off. The owner likes the depth and is keeping them. The hole's own turn is now -0.05 rad/s so that, with the camera's 0.07 orbit, hole and stars drift the same way on screen (they looked opposed before). On by default so the owner can judge it; he has not decided whether to keep them. He decided against satellites; particles falling into the hole were suggested as the one worthwhile addition, not built.

## 8v. Black hole lab: inverse mode (2026-11-15)

Colour button entry `inverse` (after white, before random): the scene is drawn in pure white on black and the final pass turns it over (`uInv`, eased; output is `1 - brightest channel`), giving white space with black lasers, black glow, black stars and a hole that reads as a paler disc. The owner calls black and white possibly the best look. Colour order: red, ember, ice, acid, violet, white, inverse, random.

## 8w. Black hole lab: rest state is now needles (2026-11-15)

The owner noticed the faint idle stubs of the beams when paused and asked for those as the rest look. With `uRest` at 1 every beam is a very faint, thin needle (length `R*(0.15+1.25*z²)`, glow `0.05*(0.35+0.65*z)`, both breathing slowly), so the hole is fully black inside a soft corona of needles. The twinkling points of 8s are switched off by a `0.*` factor in the points shader (`tw`); change it to `1.` to have both. The owner then asked for the needles at 30% of that length: `uNl` (0.675 short, after he twice asked for half as much again; 1 long), switched by the "Needles" button or key N so he can compare; short is the default. He was tempted to keep the long ones, so the choice is still open. Randomising them like the old points was mentioned and set aside.

## 8x. Black hole merged into the main app and deployed (2026-11-15)

- New mode `hole` ("Black hole" tab, between Coaster and Loom). `tools/port_blackhole.py blackhole-lab.html index.html` regenerates the module (`BHOLE` closure, `holeStep`, `holeCam`) from the lab; **change the lab and re-run, do not hand-edit the copy.**
- **Sound:** the 48-band analysis is separate from the app's own; it is computed from the decoded `buffer` about 80 ms after the mode is first opened for a song (a second or two; the resting hole shows meanwhile).
- **Wiring:** `holeOn` joins `aby` (hides the city) and `uVoid`; the app's sky dome is hidden while the hole is on (its space is plain black with its own stars); `hfPass` (hue-keeping and inverse) is added to the composer on first use and enabled only in this mode; bloom is 1.35 x theme glow, radius 1, threshold 0.05 while on; the Black out pass is forced off. Needs Quality 3 or higher for glow and inverse.
- **Controls:** drag and scroll on the canvas (only while the mode is on); a "Lasers: <colour>" pill `#holeSeg` in the top bar and key L cycle the eight palettes (C was taken by the Controls panel); the app's colour swatches, Planet, Amplify, camera switch and driving keys are hidden in this mode. Stars are always on and needles are 0.675 (the lab's two buttons were not ported, nor its glow slider).
- Checked headless on the demo: playing, paused, inverse, and switching to City and Coaster afterwards. In the main app the inverse look comes out heavier (more black) than in the lab.
- Deployed to Vercel from `main` the same morning.

## 8y. Top bar simplified (2026-11-15)

Owner's rules: **mode tabs always top centre, alone; shuffle stays visible.** A block just before the Coaster section rearranges the bar at startup: top right is Upload (icon only), Colours (or the "Lasers" pill in Black hole mode), Shuffle, Full screen, and `#btnMore` with a menu `.moremenu` holding Snapshot, Controls, Keyboard shortcuts and Hide. `#btnPlanet` is moved into `#camSeg` in the bottom bar as a fourth view (shown only where `PLANET_OK`); `#nitroWrap` (Amplify) is moved to the top of `.fxstack` as a round button. The logo no longer has a gradient behind it. `tools/port_coaster.py` now stops before the Black hole module instead of at the frame loop (it would have deleted that module). Known: the end-of-song card still talks about the city in every mode. **Later the same morning:** the views left the music bar: `#camSeg` is now a floating glass pill centred above the dock (bottom 106 px), each view with an icon (Cruise arrow, Fly paper plane, Skyline viewfinder, Planet globe); the driving keys moved up to 186 px to clear it. The landing page's three-line explainer (`.legend`) and the district signs (`#sign`) are hidden by CSS. The effects column centres all its circles on one line (`.fxstack{align-items:center}`).

## 8z. Landing text, guided tour, demo playlist (2026-11-15)

- **Landing text** is generic for all modes ("...ride the worlds it builds: a neon city, a roller coaster, a black hole firing lasers, and more").
- **Guided tour:** a block before the Coaster section. The first time a ride starts (flag `ss_tour` in localStorage) five steps ring the tabs, views pill, effects column, top-right tools and music bar with a card (Skip / Next / Esc); steps whose target is hidden are skipped. "Show me around" in the More menu (`window.__tour`) replays it. The shortcuts hint appears on its own only after the tour has been seen.
- **One landing button, "Play demo tracks":** it queues the built-in tracks as a playlist (`DEMOS=['late','house']`; playlist entries may now be a file or one of these names; `loadDemo(thenRide,keep)` and `loadHouse(keep)` keep the playlist when `keep===true`). The separate house-track button is hidden. Uploading your own songs replaces the demo playlist. **The owner wants one demo track per genre, as many as it takes:** each new one is a composition for `renderDemo(kind)` plus an entry in `DEMOS` and `plGo` (or bundled royalty-free audio files, which the static site could serve). Not done.

## 8zz. Phase 2 ideas, analysed only, nothing built (2026-11-15)

The owner sent references and asked for analysis to keep for later. Suggested order: 1, 2, 3, 4.
1. **Laser fields in smoke** (club lasers: flat fans and cones from one emitter, smoke curling inside the light). Build fans as thin triangles/planes from an emitter and cones as open cones, additive; the smoke is domain-warped fbm noise sampled on the sheet, so wisps show only where the light slices them (which is what a real laser in haze does). No true volumetrics needed. Reuses the black hole's 48-band onsets: each fan to a band, sweep angle and spread eased. Easiest of the four.
2. **Plate cymatics (Chladni figures)**: fully mathematical. Sand gathers on the nodal lines of a plate's standing waves; square plate approximately `cos(n*pi*x)cos(m*pi*y) - cos(m*pi*x)cos(n*pi*y) = 0`, round plate uses Bessel functions times `cos(k*theta)`. One fragment shader, or particles that drift to the nodes. Map pitch to (n, m): higher notes give finer figures (his 8x8 grid of tiles by note is this idea); morph between figures, eased.
3. **Water cymatics** (the glowing mandalas): real ones are Faraday waves on a dish of water photographed under a ring light. A true fluid simulation is heavy; a convincing version is a height field made of a few standing-wave modes (Bessel radial part times k-fold angular part, k and radial count from the dominant frequencies), shaded by its surface normal reflecting a ring light, which produces the bright filigree lines. Shader only; matching the photos will take tuning rounds.
4. **Light through glass** (prisms, cubes, crystals). Physically exact refraction with caustics is not realistic in real time here. Good approximations: draw the scene to a texture and let glass objects sample it bent by their surface normal, with red, green and blue bent by different amounts for the rainbow edge; three.js 0.147 `MeshPhysicalMaterial` has transmission/ior/thickness but no dispersion (added in later versions), so the rainbow split needs a custom shader. Patterns thrown onto walls (his cube-in-a-room reference, which looks computer-generated) would be drawn as projected line geometry, not computed from the glass. Hardest; most rounds.

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
