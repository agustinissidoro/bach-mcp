<!-- algo score -->
# Quantizer — markers that become measures

The score is proportional notation: times in milliseconds, no measures. It is
often the first step towards a score in classical notation. To prepare that
step, give the score **markers with a role**: time signatures, barlines, beats
and, where needed, the units inside a beat. bach.quantize reads them and writes
the measures, so the measures you mean are the ones that appear.

**Only when asked.** Write these markers when the request asks for them:
measures, a meter, barlines, a time signature, quantization, a score in
classical notation. Without such a request, write them only if the music is
built on a meter so plainly that leaving it out would lose part of the idea;
if you are in doubt, write none. A request that says nothing about measures
gets a score without markers.

When you do write them, write them while you make the music, from the same
numbers: the measure length you composed with is the distance between two
barlines.

## The roles

A marker is `{"onset": ms, "name": [], "role": ..., "content": [...]}`, in the
score's header (`header.markers`). `name` is `[]` unless you want a label.
Only `timesig` and `tempo` have a `content`; the others have none.

- **`timesig`**: a time signature, from this measure on. Content
  `[numerator, denominator]`: `[3, 4]`. An additive meter nests the numerator:
  `[[2, 2, 3], 8]`. It stands exactly where its measure starts, and **it is the
  barline of that measure**: never put a `barline` at the same onset.
- **`barline`**: the start of every other measure. The distance between two
  barlines is the length of the measure, and so its tempo. Before any
  `timesig` the meter is 4/4.
- **`division`**: a beat inside a measure. The first beat is the barline
  itself, so **a measure of n beats has n − 1 division markers**: three in 4/4,
  two in 3/4, one in 6/8 (two dotted beats).
- **`subdivision`**: a unit inside a beat; the first unit is the beat itself.
- **`tempo`**: content `[figure, value]`, the figure as text: `["1/4", 60]`.

## How much to write

Write the least that says what you mean.

- **Music on a steady grid**: the `timesig`, then a `barline` at every measure,
  and one last barline where the last measure ends. Nothing else.
- **A tempo that moves inside the measure** (rubato, accelerando, a fermata):
  add the `division` markers, at the times where the beats really fall. In
  notation the beats share the measure equally; their times bend the tempo
  beat by beat, which keeps the notes on their beats.
- **An additive meter** such as 2+2+3/8: a `division` at the start of each
  group after the first, and a `subdivision` at each other unit. The first two
  groups get one subdivision each, the last one two. Subdivisions only tell
  how the measure is grouped: their exact times do not matter, and the units of
  the measure must add up to the numerator (or divide it).
- Subdivisions in a plain meter (3/4, 4/4) change nothing when every beat has
  the same number of them. Use divisions to follow the tempo instead.
- **`tempo` markers**: only for agogics finer than the divisions can say, and
  only before the barline they belong to. Do not use them when the barlines
  and divisions already carry the timing: the two would disagree.

**A pickup.** If the music starts with an anacrusis shorter than a measure, do
not place anything at a negative time: put the `timesig` at the first real
barline, after the pickup.

**A change of meter**: a new `timesig` at the barline where it starts (in place
of that barline).

**Close the last measure**: a `barline` where it ends. A measure has a length
only when the next barline is there.

4/4, two measures of 2000 ms, then a 2+2+3/8 measure of 1750 ms:

```json
[
  {"onset": 0, "name": [], "role": "timesig", "content": [4, 4]},
  {"onset": 2000, "name": [], "role": "barline"},
  {"onset": 4000, "name": [], "role": "timesig", "content": [[2, 2, 3], 8]},
  {"onset": 4250, "name": [], "role": "subdivision"},
  {"onset": 4500, "name": [], "role": "division"},
  {"onset": 4750, "name": [], "role": "subdivision"},
  {"onset": 5000, "name": [], "role": "division"},
  {"onset": 5250, "name": [], "role": "subdivision"},
  {"onset": 5500, "name": [], "role": "subdivision"},
  {"onset": 5750, "name": [], "role": "barline"}
]
```

The tool that takes your music answers with the measures your markers make
(`measures 1-2, from 0 ms: 4/4, 2000 ms (quarter = 120) each`). Read that
line: if it is not the meter and tempo you meant, the markers are wrong.
<!-- score -->

## Writing them

- With the notes: `write_score`, the list above as `"markers"` in the
  `"header"`.
- For a score that is already there: `write_markers(markers)`. It changes the
  markers alone; the notes stay, and you do not send them again. `add: true`
  adds to the markers there instead of replacing them.
- To give measures to music you did not write, read it first (`read_score`):
  find where its beats fall, then place the barlines there.
<!-- /score -->
<!-- algo -->

## Writing them in the code

In scope, without imports. `x` is the score you are making or changing; each
call writes into its header, in time order, and writing the same marker again
replaces it:

- `timesig(x, onset, [4, 4])`, `barline(x, onset)`, `division(x, onset)`,
  `subdivision(x, onset)`, `tempo(x, onset, 60, "1/4")`.
- `grid(x, {start, timesig, bar, count, beats})`: `count` equal measures of
  `bar` milliseconds from `start`: the time signature, the barlines, and the
  one that closes the last measure. It returns that closing onset, where the
  next `grid` starts. `beats: true` also marks every beat; a nested numerator
  (`[[2, 2, 3], 8]`) always gets its divisions and subdivisions.
- `markersOf(x, role)`: the markers in time order (of one role, if given).
  `clearGrid(x)`: removes every marker that has a role; labels stay.

Derive the markers from the same values as the notes, so that a parameter
which changes the tempo or the meter moves the barlines with the music. For a
steady passage use `grid`; where the measures differ in length, loop and place
each `barline` (and its `division`s) at the time you computed for the notes.
<!-- generator -->

```js
// A rising line in 3/4 that slows down, measure by measure.
const params = {
  measures: { type: "slider", range: [2, 16], value: 6 },
  beat:     { type: "slider", range: [200, 1000], value: 400, unit: "ms" },
  slowing:  { type: "slider", range: [1, 1.3], value: 1.08 },
};

function produce(p) {
  const s = score();
  const v = s.voice("Clarinet");
  let t = 0;
  let beat = p.beat;
  for (let m = 0; m < p.measures; m++) {
    if (m === 0) timesig(s, t, [3, 4]);
    else barline(s, t);
    for (let b = 0; b < 3; b++) v.note(t + b * beat, 6000 + (m * 3 + b) * 100, beat);
    t += 3 * beat;
    beat *= p.slowing;
  }
  barline(s, t);
  return s;
}
```
<!-- /generator -->
<!-- transformer -->

A transformer writes them into the score it returns: `const out = copy(source);
clearGrid(out); grid(out, {...}); return out;`. To give measures to music that
is already there, find where its beats fall from the notes (`chordsOf`,
`iois`, `phrases`), not from fixed numbers.
<!-- /transformer -->
<!-- selector -->

A selector may also write markers: put them in `source` (`barline(source,
t)`), and still return the notes you pick (an empty list if you pick none).
They replace the markers of the roll. Each run starts from the roll's own
markers: what the previous run wrote is not there, so do not clear it.
<!-- /selector -->
<!-- /algo -->
<!-- /algo score -->
