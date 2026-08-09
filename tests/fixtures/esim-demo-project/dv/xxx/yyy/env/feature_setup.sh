#!/usr/bin/env bash

: "${DV_HOME:?set DV_HOME before sourcing feature_setup.sh}"

export ESIM_DEMO_CONFIG_ROOT="$DV_HOME/xxx/yyy"
export ESIM_DEMO_YYY_RULES='$ESIM_DEMO_CONFIG_ROOT/rules'
export ESIM_DEMO_YYY_TESTS='${ESIM_DEMO_CONFIG_ROOT}/tests'
export ESIM_DEMO_FILELIST='$ESIM_DEMO_CONFIG_ROOT/tb/full.f'
export ESIM_DEMO_COMMON_FILELIST="$DV_HOME/xxx/yyy/tb/top.f"
export ESIM_DEMO_LABEL="alpha beta"
export ESIM_DEMO_SEED=23
export FF_DEMO_ROOT='$ESIM_DEMO_CONFIG_ROOT/tb/ff_features'
export FF_DEMO_SOURCE_ROOT='${FF_DEMO_ROOT}/sources'
export FF_DEMO_INCLUDE_ROOT='$FF_DEMO_ROOT/include'
export FF_DEMO_LIBRARY_FILE='$FF_DEMO_ROOT/library/ff_demo_cells.sv'
export FF_DEMO_LIBRARY_DIR='${FF_DEMO_ROOT}/library/search'
export FF_DEMO_WORKING_FILELIST='$FF_DEMO_ROOT/working/working.f'
