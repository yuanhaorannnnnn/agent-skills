# CARLA Sensor Design Variant

Load this reference only for CARLA sensor development proposals. It specializes
the generic CONOPS sections without changing the 14-section top-level contract.

## Section 4: User-visible Behavior

Use these subsections when the corresponding interface exists:

### 4.1 Blueprint

- blueprint id
- relationship to existing sensor blueprints
- exposed attributes, defaults, units, valid ranges, and compatibility

### 4.2 Python Callback

- callback type
- data access path
- smallest runnable code example
- timestamp/frame semantics and payload ownership when relevant

### 4.3 DFS / Proto Data

- message type
- field list and units
- serialization/version compatibility
- explicitly state when DFS/Proto is out of scope

### 4.4 Typical Configuration

List every exposed parameter in a table:

| Parameter | Default | Meaning / Unit |
|---|---|---|

Do not replace the table with "same as another sensor".

## Section 7: Protocol and Data Model

Cover only implemented or approved contracts:

- Unreal/C++ sensor data type and serialization boundary
- Python API payload and accessor
- DFS/Proto message and field mapping
- coordinate frame, units, timestamp, invalid-value convention
- backward compatibility and versioning

Separate declaration/parser existence from verified runtime support.

## Section 9: Test Review Points

Use relevant layers:

1. compile/static contract
2. blueprint discovery and attribute defaults
3. Python callback and payload semantics
4. runtime sensor output
5. DFS/Proto transport
6. reference or consistency comparison
7. performance and packaging when in scope

For every layer, distinguish planned, statically checked, built, runtime tested,
and acceptance-threshold verified.
