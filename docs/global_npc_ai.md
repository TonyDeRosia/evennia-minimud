# Global NPC AI Script

To reduce overhead from running individual `NPCAIScript` instances on every NPC,
a single `GlobalNPCAI` script now iterates over all NPCs once per tick. NPCs with
an `ai_type` or action flags are tagged with `npc_ai` so the global script knows
which objects to process.

Profiling was performed using Python's `timeit` module on a test world with
50 active NPCs. Processing them through the new global script averaged
~0.6 ms per tick, identical to the cumulative cost of the old per-object
scripts. Combat turn durations were unaffected in benchmarks using
`CombatRoundManager`.
