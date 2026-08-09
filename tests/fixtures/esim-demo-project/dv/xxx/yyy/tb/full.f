// ff complete positive scenario consumed by esim and VCS.
+define+FF_INPUT_TOP
+incdir+$FF_DEMO_INCLUDE_ROOT/primary+$FF_DEMO_INCLUDE_ROOT/secondary // complete demo include directories

`ifdef COMPLETE_YYY
-F ff_features/conditions.f
-f $FF_DEMO_WORKING_FILELIST
-f $DV_HOME/xxx/yyy/tb/filelists/feature.f
-F ff_features/nested/root.f
-F ff_features/options.f
-F ff_features/symlink.f
-F filelists/rtl.f
`else
$DV_HOME/xxx/yyy/tb/rtl/inactive_missing.sv
`endif
-F filelists/tb.f
