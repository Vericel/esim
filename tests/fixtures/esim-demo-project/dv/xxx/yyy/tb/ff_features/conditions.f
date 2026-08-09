/* active conditional matrix */
`ifdef COMPLETE_LEFT
  `ifndef FF_DEMO_DISABLED
$FF_DEMO_SOURCE_ROOT/condition_left.sv // ifndef branch
  `else
$FF_DEMO_SOURCE_ROOT/inactive_missing.sv
  `endif
`elsif COMPLETE_RIGHT
$FF_DEMO_SOURCE_ROOT/inactive_missing.sv
`else
$FF_DEMO_SOURCE_ROOT/inactive_missing.sv
`endif

`ifdef FF_DEMO_NEVER_DEFINED
$FF_DEMO_SOURCE_ROOT/inactive_missing.sv
`elsif COMPLETE_RIGHT
${FF_DEMO_SOURCE_ROOT}/condition_right.sv
`else
$FF_DEMO_SOURCE_ROOT/inactive_missing.sv
`endif
