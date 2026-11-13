# coolest-art-02 — BUILD_NOTES (v2 entry for coolest-art-01)

## Entry
**"Dragon Over the Burning Mountain"** — a great dragon silhouetted against
a blood moon, wings spread, crossing the sky above an erupting volcano. Lava
streams run down the cone, embers rise into the red sky, a river of fire
cuts the foreground. Program: `main.py` (Python 3.13, standard library
only), ~640 lines, ~23 KB source. This is a DIFFERENT scene from the v1
entry ("The Ringed Giant", ringed planet over a teal sea) — built as a
second, cooler entry for the same bounty.

## Why this composition (judge criteria, most important first)
1. **Stops the eye:** a huge pale blood moon fills the upper right, with the
   black dragon crossing it — the highest-contrast shape in the piece, and
   the classic "dragon crossing the moon" shot.
2. **Idea:** mythic scale + action — a dragon in flight over an erupting
   volcano, embers rising, lava river below. Fire, flight, and a giant moon
   in one frame; a stronger "cool" story than a static planet.
3. **Style:** one mood (ominous / burning dusk), one palette: deep
   maroon-red sky, pale cream moon, near-black silhouettes, bright orange
   lava and rim light.
4. **Craft:** pure geometry (polygons, tapering tubes, ellipses, gradients)
   — mathematically exact, so no smears, no garbled text (there is no
   text), no broken anatomy. The dragon is a silhouette, so anatomy can't
   break: body tube, scalloped bat-wing polygons, horned head, tucked legs,
   spade tail, one burning-orange eye.
5. **Reads small:** at ~300 px the moon + dragon + volcano + lava river
   are still unmistakable.

## Technique
- Hand-written PNG encoder (stdlib `zlib` + `struct`, reused from the v1
  entry's proven encoder): signature, IHDR, IDAT with adaptive per-row
  filter (None/Sub/Up/Average/Paeth chosen by minimum
  sum-of-absolute-values heuristic), zlib level 9, correct CRCs.
- Renderer: sky gradient with a warm lift above the volcano, faint stars,
  moon halo (radial falloff) + disk with limb darkening, mottling and
  craters, distant ridges, volcano cone with a vertical gradient (lighter
  near the crater), crater glow + lava pool, four jagged lava streams
  (glow / main / hot core passes), lava river with hot core band, yellow
  streaks and rim-lit rocks, smoke plume (layered translucent puffs, soft
  halo + textured inner circles, drifting right, kept clear of the moon),
  embers in two layers (behind and in front of the dragon, some with
  rising trails, a few big glowing ones), dragon in two passes (rim-light
  copy offset toward the moon, then the black silhouette), vignette.
- Drawing primitives: `fill_circle`, `fill_ellipse`, scanline `fill_poly`
  (handles concave wing polygons), `stroke`, tapering `tube` along a
  polyline with per-point radii.
- Determinism: fixed seed (`SEED = 20261114`, `random.Random` instances
  only), no clock/time/network/dict-order dependence. Output dir from
  `$MAKEFUN_OUTPUT_DIR`, else `/output` (verified both).

## Test results (2026-11-13, this session)
- Two runs, `MAKEFUN_OUTPUT_DIR=out1` / `out2`: **byte-identical**
  (sha256 `5561b60a4d5dac2c3be5ede4b2a93e4cf4b58d3b40620305a22a0ce8b795f5a9`).
- Output: **1024×1024, 190,112 bytes** (limit 1,048,576) — valid PNG:
  signature, all chunk CRCs, IHDR (8-bit, colour type 2 RGB), IDAT
  decompresses to exactly 3,146,752 bytes.
- Runtime: **~10 s** (limit 60 s), single-threaded CPython.
- Default path: running with no `MAKEFUN_OUTPUT_DIR` writes `/output/entry.png`.
- Imports: `math, os, random, struct, zlib` — stdlib only, no network.
- One bug found and fixed during testing: the cone-gradient colour was a
  float tuple (bytearray assignment raised `TypeError`) — now cast to int.

## Visual revisions (v2 was inspected as an image, twice)
- **Draft 1 (rejected):** the dragon did not read — body too thin/long
  (looked like a snake), wing bones drawn as straight strokes to the
  wingtip crossed the moon like stray sticks, smoke plume was muddy grey
  disks overlapping the moon, volcano cone was a flat black triangle, lava
  river rocks looked like floating black holes.
- **Draft 2 (final):** moon enlarged (R 155 → 210) and the dragon moved so
  its whole body crosses the moon; body thickened (chest radius 38);
  wing bones removed (the scalloped membrane reads cleaner as a pure
  silhouette); smoke softened (halo + low-alpha textured circles), lowered
  and kept clear of the moon; cone given a vertical gradient; river rocks
  replaced with rim-lit half-submerged rocks at the river's top edge.
  Inspected as an image and judged striking: dragon + moon + volcano +
  lava all read cleanly.

## Kit rules note (vendored image)
As with v1, RULES.txt allows the copy-a-vendored-image route, but this
entry deliberately takes the draw-it route — the program draws the art —
so the image is fully reproducible from the transcripts and the
entrypoint's authored lines. No image asset is vendored.

## Files in this directory
- `main.py` — the entry program.
- `preview.png` — copy of the verified output (`out1/entry.png`).
- `out1/`, `out2/` — the two determinism-test outputs.

## Not done here (parent's steps)
No GitHub repo created, nothing submitted, no accounts/keypairs created.
Next: repo under GitHub `ysfrhmnsh` (LICENSE with SPDX line, main.py at
root, `.makefun/owner.json` with the agent wallet), bundle transcripts,
`check`, submit before Fri 2026-11-13 10:00 UTC (17:00 WIB). Note: v1
("The Ringed Giant") was already submitted as entry 1 for this bounty;
this v2 is the resubmission/upgrade entry the user ordered.
