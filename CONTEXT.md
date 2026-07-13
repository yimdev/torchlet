# Torchlet

Torchlet presents LLM inference as a sequence of small, readable implementation stages. Its language emphasizes how each stage responds to the design pressure left visible by the preceding stage.

## Language

**Version**:
A named implementation stage that preserves one form of the inference path so its design changes can be examined in sequence.
_Avoid_: Release, revision

**Version evolution**:
The progression of design ideas from an earlier Version to a later Version, including both the newly introduced idea and the tradeoff it addresses.
_Avoid_: Release history, changelog

**Design pressure**:
A limitation deliberately left visible in one Version that motivates the next step in Version evolution.
_Avoid_: Feature request, defect

**Version comparison**:
A directed examination of the code changes between a base Version and a target Version, intended to explain Version evolution.
_Avoid_: Generic diff, code review

**Base Version**:
The earlier Version from which a Version comparison begins.
_Avoid_: Left version, old version

**Target Version**:
The later Version whose changes a Version comparison explains.
_Avoid_: Right version, new version
