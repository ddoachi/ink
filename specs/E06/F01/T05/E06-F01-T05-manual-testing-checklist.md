# Manual Testing Checklist: E06-F01 Main Window Shell

**Version**: 0.1.0
**Date**: 2025-12-27
**Spec Reference**: E06-F01-T05

---

## Purpose

This checklist provides systematic manual testing for the Main Window Shell feature.
While automated tests cover most functionality, visual appearance and user interaction
nuances require human verification.

## Test Environment Setup

- **OS**: _______________________ (e.g., Ubuntu 22.04 LTS)
- **Desktop**: _______________________ (e.g., GNOME 44, KDE Plasma 5.27)
- **Display**: _______________________ (e.g., Wayland, X11)
- **Screen**: _______________________ (e.g., 1920x1080 @ 100% scale)
- **Date**: _______________________
- **Tester**: _______________________

---

## TC-01: Application Launch

**Objective**: Verify application launches correctly

### Steps:
1. Open terminal
2. Navigate to project root
3. Run: `uv run python -m ink`

### Expected Results:
- [ ] Application launches without errors
- [ ] Window appears within 2 seconds
- [ ] Console shows startup log messages
- [ ] No error or warning messages in console

### Actual Results:
_________________________________________________________________

---

## TC-02: Window Title and Appearance

**Objective**: Verify window visual appearance

### Steps:
1. Launch application
2. Observe window title bar

### Expected Results:
- [ ] Window title: "Ink - Incremental Schematic Viewer"
- [ ] Window has standard decorations (title bar, borders)
- [ ] Title bar has minimize, maximize, close buttons
- [ ] Window decorations match system theme

### Actual Results:
_________________________________________________________________

---

## TC-03: Layout Structure

**Objective**: Verify panel layout is correct

### Steps:
1. Launch application
2. Observe panel positions and sizes

### Expected Results:
- [ ] Central area shows "Schematic Canvas Area" placeholder
- [ ] Left panel shows "Hierarchy Panel" placeholder
- [ ] Right panel shows "Properties Panel" placeholder
- [ ] Bottom panel shows "Message Panel" placeholder
- [ ] All panel titles visible in dock title bars
- [ ] Canvas occupies majority of window area
- [ ] Panels have proper spacing (no overlap)

### Actual Results:
_________________________________________________________________

---

## TC-04: Visual Polish

**Objective**: Verify UI polish styling is applied

### Steps:
1. Launch application
2. Observe visual styling elements

### Expected Results:
- [ ] Main window background is light gray (#f5f5f5)
- [ ] Dock title bars have subtle styling
- [ ] Panel content areas are white
- [ ] Splitter handles are visible (2px width)
- [ ] Splitter handles highlight on hover
- [ ] No visual glitches or rendering issues

### Actual Results:
_________________________________________________________________

---

## TC-05: Dock Widget Closing

**Objective**: Verify docks can be closed

### Steps:
1. Launch application
2. Click close button (X) on hierarchy dock
3. Click close button on property dock
4. Click close button on message dock

### Expected Results:
- [ ] Each dock hides when close button clicked
- [ ] Canvas expands to fill vacated space
- [ ] No errors in console
- [ ] Application remains responsive

### Actual Results:
_________________________________________________________________

---

## TC-06: Dock Widget Floating

**Objective**: Verify docks can be floated and re-docked

### Steps:
1. Launch application
2. Drag hierarchy dock title bar away from window
3. Observe floating dock
4. Drag floating dock back to left edge
5. Observe re-docking

### Expected Results:
- [ ] Dock undocks smoothly when dragged away
- [ ] Floating dock becomes separate window
- [ ] Floating dock has window decorations
- [ ] Drop zone highlight appears when dragging near window edge
- [ ] Dock re-docks when dropped in allowed area
- [ ] Dock returns to correct position after re-docking

### Actual Results:
_________________________________________________________________

---

## TC-07: Splitter Resizing

**Objective**: Verify panel splitters work

### Steps:
1. Launch application
2. Position mouse on boundary between hierarchy panel and canvas
3. Observe cursor change
4. Drag splitter left/right
5. Repeat for property panel and message panel boundaries

### Expected Results:
- [ ] Splitter handle visible (subtle gray line)
- [ ] Cursor changes to resize cursor on hover
- [ ] Splitter handle highlights on hover
- [ ] Dragging splitter resizes panels smoothly
- [ ] No visual glitches during resize
- [ ] Panels resize proportionally

### Actual Results:
_________________________________________________________________

---

## TC-08: Window Controls

**Objective**: Verify window controls work

### Steps:
1. Launch application
2. Click minimize button
3. Restore window from taskbar
4. Click maximize button
5. Click maximize again (or restore button) to restore
6. Drag title bar to move window
7. Click close button

### Expected Results:
- [ ] Minimize: Window hides to taskbar
- [ ] Restore: Window reappears at previous position
- [ ] Maximize: Window fills screen
- [ ] Restore: Window returns to previous size/position
- [ ] Move: Window moves smoothly when title dragged
- [ ] Close: Window closes, application exits cleanly

### Actual Results:
_________________________________________________________________

---

## TC-09: Window Resizing

**Objective**: Verify window resize behavior

### Steps:
1. Launch application
2. Drag window bottom-right corner to resize larger
3. Drag to resize smaller
4. Try to resize below minimum (1024x768)

### Expected Results:
- [ ] Window resizes smoothly when dragged
- [ ] Panels scale proportionally with window
- [ ] Cannot resize below 1024x768 minimum
- [ ] All content remains visible during resize
- [ ] No layout glitches during resize

### Actual Results:
_________________________________________________________________

---

## TC-10: Dock Tabbing

**Objective**: Verify docks can be tabbed together

### Steps:
1. Launch application
2. Drag property dock to left area (on top of hierarchy dock)
3. Observe tabbed interface
4. Click each tab to switch
5. Drag property tab back to right side

### Expected Results:
- [ ] Property dock tabs with hierarchy when dropped on top
- [ ] Tabs visible at bottom of dock area
- [ ] Clicking tab switches active panel
- [ ] Panel content switches correctly
- [ ] Dragging tab out separates docks
- [ ] Dock returns to original position

### Actual Results:
_________________________________________________________________

---

## TC-11: Menu Bar

**Objective**: Verify menu bar functionality

### Steps:
1. Launch application
2. Click "File" menu
3. Observe submenu contents
4. Click "Help" menu
5. Observe submenu contents

### Expected Results:
- [ ] File menu opens when clicked
- [ ] File menu contains: Open, Open Recent >, Exit
- [ ] Open Recent submenu shows "(No recent files)" initially
- [ ] Help menu opens when clicked
- [ ] Help menu contains: About
- [ ] Menus close when clicking elsewhere
- [ ] Keyboard shortcuts shown (if defined)

### Actual Results:
_________________________________________________________________

---

## TC-12: Application Exit

**Objective**: Verify clean shutdown

### Steps:
1. Launch application
2. Close window via close button
3. Observe console output
4. Check for zombie processes: `ps aux | grep ink`

### Expected Results:
- [ ] Console shows clean exit (no errors)
- [ ] Terminal prompt returns
- [ ] No zombie processes remain
- [ ] Exit code is 0 (check with `echo $?`)

### Actual Results:
_________________________________________________________________

---

## TC-13: Dock Animation

**Objective**: Verify dock animations are smooth

### Steps:
1. Launch application
2. Slowly drag hierarchy dock to float
3. Slowly drag floating dock back to dock
4. Observe animation during transition

### Expected Results:
- [ ] Dock float/unfloat has smooth animation
- [ ] Drop zone indicators appear smoothly
- [ ] No visual stuttering or flicker

### Actual Results:
_________________________________________________________________

---

## TC-14: Startup Performance

**Objective**: Verify startup time requirement

### Steps:
1. Close all Ink instances
2. Run: `time uv run python -m ink &`
3. Observe window appearance
4. Close window
5. Note time from output

### Expected Results:
- [ ] Startup time < 2 seconds (hard requirement)
- [ ] Window appears quickly with no perceived lag
- [ ] No visible delay before window content appears

### Actual Time: __________ seconds

---

## TC-15: High-DPI Display (if available)

**Objective**: Verify high-DPI support

### Test on each available configuration:
- [ ] 1080p @ 100% scale
- [ ] 1080p @ 125% scale
- [ ] 1080p @ 150% scale
- [ ] 4K @ 200% scale (if available)

### Expected Results:
- [ ] Window scales appropriately for DPI
- [ ] Text is sharp and readable at all scales
- [ ] Panel sizes are reasonable
- [ ] No clipping or element overlap
- [ ] Splitter handles visible at all scales

### Actual Results:
_________________________________________________________________

---

## Summary

**Total Test Cases**: 15
**Passed**: _____
**Failed**: _____
**Blocked**: _____
**N/A**: _____

**Overall Result**: PASS / FAIL

**Issues Found**:
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

**Recommendations**:
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

**Sign-off**:

- Tester: _________________________ Date: _____________
- Reviewer: _________________________ Date: _____________
