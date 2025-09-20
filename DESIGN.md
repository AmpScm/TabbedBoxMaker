# TabbedBoxMaker Architecture Design

## Current State Analysis

### Current Architecture (Legacy)
The current system has evolved organically and has several architectural coupling issues:

1. **Piece Creation**: Box pieces are created with hardcoded dimension mappings
2. **Tab System**: Dual boolean system (`is_male`, `has_tabs`) with geometric coupling
3. **Rendering**: Render functions calculate geometric offsets on-the-fly using neighboring side knowledge
4. **Coordinate Systems**: Each side calculates its own coordinate system during rendering
5. **Geometric Knowledge**: Scattered across rendering functions rather than encapsulated

### Current Data Flow
```
User Input → BoxSettings → TabConfiguration → Pieces → Individual Sides → Render Functions
                                                    ↓
                               Calculate offsets based on neighboring sides during render
```

### Known Issues
- **Geometric Coupling**: `is_male` boolean overloaded for both tab direction AND geometric offset calculation
- **Scattered Logic**: Coordinate calculations spread across multiple render functions
- **Side Interdependence**: Each side must know about its neighbors during rendering
- **Workarounds**: Divider creation sets `is_male=True` when `has_tabs=False` for geometry

## Target Architecture (Mathematical Model)

### Vision: 3D Vector-Based Design
Transform the system to use proper mathematical foundations:

```
3D Box Model → 2D Piece Geometry → 2D Layout Transform → Final SVG
```

### Core Principles

#### 1. 3D Cube as Foundation
- Start with a mathematical 3D cube representation
- Each face is a 3D plane with normal vector
- Tab directions are 3D vectors
- Piece orientations are rotation matrices

#### 2. Proper Coordinate Systems
```
Face Coordinate System:
- Each piece knows its position on the 3D cube
- Each side knows its direction vector relative to face
- Geometric transforms handle coordinate conversion
```

#### 3. Separation of Concerns
- **Piece Generation**: Pure 3D → 2D geometry conversion
- **Tab Logic**: Clean enum-based system (NONE/MALE/FEMALE)
- **Layout**: Pure 2D positioning transforms
- **Rendering**: Simple path generation with pre-calculated coordinates

#### 4. Transform Pipeline
```
3D Face Definition
    ↓ (Face Normal + Thickness Vector)
2D Piece Geometry
    ↓ (Rotation Matrix)
Oriented 2D Piece
    ↓ (Translation Vector)
Final Layout Position
```

### Target Data Flow
```
User Input → 3D Box Model → Face Definitions → 2D Pieces → Layout Transform → SVG
                                ↓
                        Pre-calculated geometric offsets
```

## Migration Strategy

### Phase 1: Foundation Improvements ✅ (Completed)
- [x] Add `inside_length`/`outside_length` to Side class
- [x] Centralize dimension calculation logic
- [x] Simplify `make_sides()` interface
- [x] Reduce parameter passing complexity

### Phase 2: Geometric Decoupling (Current Focus)
- [ ] **Step 2.1**: Pre-calculate geometric offsets in Side/Piece creation
  - Add offset properties to Side class
  - Calculate offsets after side linking
  - Update render functions to use pre-calculated values
- [ ] **Step 2.2**: Eliminate side interdependence in rendering
  - Each side renders independently using its own coordinate system
  - Remove neighbor knowledge from render functions
- [ ] **Step 2.3**: Fix tab enum coupling
  - Separate tab presence/direction from geometric calculation
  - Replace dual booleans with single SideTabbing enum

### Phase 3: Coordinate System Unification
- [ ] **Step 3.1**: Define standard face coordinate systems
  - Each face has consistent coordinate orientation
  - Define transforms between face and global coordinates
- [ ] **Step 3.2**: Implement side direction vectors
  - Replace side-specific logic with vector calculations
  - Use rotation matrices for 90-degree turns
- [ ] **Step 3.3**: Unify render logic
  - Single render function with transforms
  - Eliminate per-side render variations

### Phase 4: 3D Mathematical Foundation
- [ ] **Step 4.1**: Define 3D box model
  - Face normal vectors
  - Thickness vectors
  - Edge definitions
- [ ] **Step 4.2**: Implement 3D → 2D projection
  - Face plane projection
  - Proper perspective handling
- [ ] **Step 4.3**: Vector-based tab calculation
  - Tab directions as 3D vectors
  - Geometric offsets from vector algebra

### Phase 5: Clean Architecture
- [ ] **Step 5.1**: Pure function design
  - Immutable piece definitions
  - Stateless transforms
- [ ] **Step 5.2**: Enhanced testing
  - Transform verification
  - Geometric property tests
- [ ] **Step 5.3**: Performance optimization
  - Pre-compute expensive calculations
  - Cache transform matrices

## Implementation Guidelines

### Safety First
- **Regression Tests**: All 156 tests must pass at each step
- **Small Changes**: Each step should be minimal and verifiable
- **Backward Compatibility**: Maintain existing interfaces during transition
- **Incremental**: Build new system alongside old, then replace

### Key Insights for Next Steps

#### Current Blocker: Geometric Coupling
The `is_male` boolean serves dual purposes:
1. Tab direction (logical)
2. Geometric offset calculation (physical)

This prevents clean enum replacement. The solution is to separate these concerns by pre-calculating geometric offsets.

#### Next Safe Step: Offset Pre-calculation
1. Add offset properties to Side class
2. Calculate offsets after side linking in Piece constructor
3. Update render functions to use pre-calculated values
4. Verify identical output with regression tests

#### Mathematical Foundation Goal
Eventually, geometric offsets should be calculated from:
- Face normal vector
- Thickness vector
- Edge direction vector

Instead of boolean flags about neighboring sides.

## Testing Strategy

### Current Test Coverage
- 156 regression tests covering various box configurations
- Tests verify SVG output exactness
- Covers edge cases like dividers, different layouts, Schroff boxes

### Additional Testing Needed
- **Transform Verification**: Test mathematical properties
- **Coordinate System Tests**: Verify coordinate conversions
- **Geometric Properties**: Test that box pieces fit together
- **Performance Tests**: Ensure no regression in generation speed

## Benefits of Target Architecture

### For Users
- **Consistency**: Predictable behavior across all box types
- **Flexibility**: Easy to add new box shapes and features
- **Quality**: Mathematically correct geometry

### For Developers
- **Maintainability**: Clear separation of concerns
- **Extensibility**: Easy to add new features
- **Debuggability**: Mathematical properties are verifiable
- **Performance**: Pre-calculated values reduce computation

### For Future Features
- **3D Visualization**: Direct 3D model availability
- **Custom Shapes**: Easy to define new geometries
- **Advanced Layouts**: Complex positioning becomes simple transforms
- **Validation**: Mathematical constraints can be verified

## Current Priority

Focus on **Phase 2.1**: Pre-calculate geometric offsets. This is the critical step that will break the coupling between rendering logic and neighboring side knowledge, enabling all subsequent improvements while maintaining test compatibility.