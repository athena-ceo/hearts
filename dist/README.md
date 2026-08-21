# HEARTS — a 1986 InterLisp-D card game, revived for Medley

This directory is the loadable distribution of **HEARTS**, an expert-system Hearts game
originally written in InterLisp-D + KEE for MIT 6.871 (spring 1986) by Harley Davis and
Ramana Rao, brought back to life on modern [Medley Interlisp](https://interlisp.org/).

Three player types work today — **Clown** (random legal), **Conservative** (rule-based AI),
and **Human** (you, clicking cards). The KEE-based **Expert** player is not included (KEE is
proprietary and gone); see the project root for the revival story and the plan to reimplement it.

## Files

| File | What it is |
|------|------------|
| `ACTIVEREGIONS` | A standalone lispusers module: clickable/highlightable window regions, driven by the window `BUTTONEVENTFN`. A drop-in stand-in for the 1986 INTERMEZZO library of the same name, which modern Medley no longer ships. Reusable on its own. |
| `HEARTS` | The game. `(FILESLOAD ACTIVEREGIONS)`s the above, then defines everything else. |

## Load & run

1. Copy `ACTIVEREGIONS` and `HEARTS` into a directory Medley can reach (e.g. `~/il/`).
2. In the Medley **Exec** (Interlisp package), connect to that directory and load:

   ```
   (FILESLOAD ACTIVEREGIONS HEARTS)
   ```

3. Start a game. The argument is the four seats, clockwise:

   ```
   (LHearts '(HP CP CP CP))     ; you (Human) vs three Conservatives
   (LHearts '(CP CP CP CP))     ; four Conservatives play themselves
   (LHearts '(CLOWN CLOWN CLOWN CLOWN))   ; four random-legal Clowns
   ```

   `HP` = Human player, `CP` = Conservative, `CLOWN` = Clown.

4. For the human game you'll be prompted for your name, then a **Hearts Window** opens with
   your hand. Click a card to select it, then use the **Play** item on the window's menu.
   Turn on the Conservatives' running commentary with `(SETQ ThinkFlag? T)` before you start.

## Notes for macOS / SDL users

Medley on macOS runs headless-ish through the SDL backend (`--maikoprog ldesdl`, no XQuartz).
Setup gotchas we hit (framework install, an `install_name_tool` rpath fix, ad-hoc re-signing,
and a clipboard/subprocess caveat) are written up in the project's `MEDLEY-ISSUES.md`.

## Provenance

- Faithful transcription of the original listing lives in `transcription/` at the project root.
- The loadable `HEARTS` here is that transcription with mechanical revival patches folded in
  (a handful of definitions the 1986 running image had but the paper listing didn't, plus a few
  original-1986 bug fixes). Every patch is documented in `HEARTS-BUGS.md` at the project root.
- Icons are stubbed (the two 50×50 icon bitmaps were lost); the five card bitmaps are recovered
  and real, so suits draw legibly.

To recompile for speed inside Medley: `(MAKEFILE 'ACTIVEREGIONS)` then `(TCOMPL 'ACTIVEREGIONS)`,
and likewise for `HEARTS` — then ship the resulting `.DCOM`s.
