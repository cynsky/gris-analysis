#!/bin/bash

# run in green-hydro/run

set -e -x

# set type from argument 1
pgs=250
if [ -n "$1" ]; then
    pgs=$1
fi

ver=2
nc_dir=processed
pr_dir=profiles
reg_dir=regional
obs_dir=observed
fig_dir=figures

CLIMATE=const
TYPE=ctrl_v${ver}


GRID=900
tl_dir=${GRID}m_${CLIMATE}_${TYPE}

out_suffix=best_flow_v${ver}
for region in "jakobshavn"; do
    for saryears in "2008-2009"; do
        for var in "velsurf_normal"; do
            ./flux-gate-analysis.py  --colormap YlGnBu sequential 4 0 -p medium --label_params 'ssa_Glen_exponent,pseudo_plastic_q,bed_data_set' --no_legend -v ${var} --plot_title --obs_file $obs_dir/$pr_dir/profiles_${pgs}m_${region}_${saryears}_observed_flux_v${ver}.nc $tl_dir/$pr_dir/profiles_${pgs}m_${region}_g${GRID}m_${CLIMATE}_${TYPE}_sia_e_1.25_ppq_0.6_tefo_0.02_ssa_n_3.25_ssa_e_1.0_philow_5.0_hydro_null_100a.nc 900m_const_cresis_v2/profiles/profiles_250m_jakobshavn_g900m_const_cresis_v2_sia_e_1.25_ppq_0.6_tefo_0.02_ssa_n_3.25_ssa_e_1.0_philow_5.0_hydro_null_100a.nc
            for file in *_${var}_profile.pdf; do            
                bfile=$(basename $file .pdf)
                mv $file ${bfile}_${pgs}m_${region}_${saryears}_${out_suffix}.pdf
            done
            for file in rmsd_experiment_*_${var}.tex; do
                bfile=$(basename $file .tex)
                mv $file ${bfile}_${pgs}m_${region}_${saryears}_${out_suffix}.tex
            done
            ./flux-gate-analysis.py --colormap YlGnBu sequential 4 0 -p small_font --legend long --label_params 'ssa_Glen_exponent,pseudo_plastic_q,bed_data_set'  -v ${var} --obs_file $obs_dir/$pr_dir/profiles_${pgs}m_${region}_${saryears}_observed_flux_v${ver}.nc $tl_dir/$pr_dir/profiles_${pgs}m_${region}_g${GRID}m_${CLIMATE}_${TYPE}_sia_e_1.25_ppq_0.6_tefo_0.02_ssa_n_3.25_ssa_e_1.0_philow_5.0_hydro_null_100a.nc 900m_const_cresis_v2/profiles/profiles_250m_jakobshavn_g900m_const_cresis_v2_sia_e_1.25_ppq_0.6_tefo_0.02_ssa_n_3.25_ssa_e_1.0_philow_5.0_hydro_null_100a.nc
            for file in *_${var}_profile.pdf; do
                bfile=$(basename $file .pdf)
                mv $file ${bfile}_${pgs}m_${region}_${saryears}_${out_suffix}_long_label.pdf
            done
            for file in pearson_r_experiment_*_${var}.pdf; do
                bfile=$(basename $file .pdf)
                mv $file ${bfile}_${pgs}m_${region}_${saryears}_${out_suffix}.pdf
            done
            mv statistics.shp statistics_${var}_${pgs}m_${region}_${saryears}_${GRID}m_${out_suffix}.shp
            mv statistics.dbf statistics_${var}_${pgs}m_${region}_${saryears}_${GRID}m_${out_suffix}.dbf
            mv statistics.prj statistics_${var}_${pgs}m_${region}_${saryears}_${GRID}m_${out_suffix}.prj
            mv statistics.shx statistics_${var}_${pgs}m_${region}_${saryears}_${GRID}m_${out_suffix}.shx
             # ./flux-gate-analysis.py --colormap YlGnBu sequential 4 0 -p small_font --legend long --label_params 'bed_data_set'  -v ${var} --obs_file $obs_dir/$pr_dir/profiles_${pgs}m_${region}_${saryears}_observed_flux_v${ver}.nc $tl_dir/$pr_dir/profiles_${pgs}m_${region}_g${GRID}m_${CLIMATE}_${TYPE}_sia_e_1.25_ppq_0.6_tefo_0.0175_ssa_n_3.0_ssa_e_0.8_philow_5.0_hydro_null_100a.nc ${GRID}m_${CLIMATE}_old_bed/$pr_dir/profiles_${pgs}m_${region}_g${GRID}m_${CLIMATE}_old_bed_e_1.25_ppq_0.6_tefo_0.02_ssa_n_3.25_philow_5.0_hydro_null_100a.nc
        done
        # for var in "flux_normal"; do
        #     ./flux-gate-analysis.py --export_table_file ${var}-gate-table-all-${pgs}m.tex --colormap YlGnBu sequential 4 0 -p medium --label_params 'ssa_Glen_exponent,pseudo_plastic_q,bed_data_set' --legend long -v ${var} --plot_title --obs_file $obs_dir/$pr_dir/profiles_${pgs}m_${region}_${saryears}_observed_flux_v${ver}.nc $tl_dir/$pr_dir/profiles_${pgs}m_${region}_g${GRID}m_${CLIMATE}_${TYPE}_sia_e_1.25_ppq_0.6_tefo_0.0175_ssa_n_3.0_ssa_e_0.8_philow_5.0_hydro_null_100a.nc
        #     for file in *_${var}_profile.pdf; do
        #         bfile=$(basename $file .pdf)
        #         mv $file ${bfile}_${pgs}m_${region}_${saryears}_${out_suffix}.pdf
        #     done
        #     for file in rmsd_experiment_*_${var}.tex; do
        #         bfile=$(basename $file .tex)
        #         mv $file ${bfile}_${pgs}m_${region}_${saryears}_${out_suffix}.tex
        #     done
        #     ./flux-gate-analysis.py --colormap YlGnBu sequential 4 0 -p small_font --legend long --label_params 'ssa_Glen_exponent,pseudo_plastic_q,bed_data_set'  -v ${var} --obs_file $obs_dir/$pr_dir/profiles_${pgs}m_${region}_${saryears}_observed_flux_v${ver}.nc $tl_dir/$pr_dir/profiles_${pgs}m_${region}_g${GRID}m_${CLIMATE}_${TYPE}_sia_e_1.25_ppq_0.6_tefo_0.0175_ssa_n_3.0_ssa_e_0.8_philow_5.0_hydro_null_100a.nc
        #     for file in skill_score_experiment_*_${var}.pdf; do
        #         bfile=$(basename $file .pdf)
        #         mv $file ${bfile}_${pgs}m_${region}_${saryears}_${out_suffix}.pdf
        #     done
        #     for file in pearson_r_experiment_*_${var}.pdf; do
        #         bfile=$(basename $file .pdf)
        #         mv $file ${bfile}_${pgs}m_${region}_${saryears}_${out_suffix}.pdf
        #     done
        #     mv statistics.shp statistics_${var}_${pgs}m_${region}_${saryears}_${GRID}m_${out_suffix}.shp
        #     mv statistics.dbf statistics_${var}_${pgs}m_${region}_${saryears}_${GRID}m_${out_suffix}.dbf
        #     mv statistics.prj statistics_${var}_${pgs}m_${region}_${saryears}_${GRID}m_${out_suffix}.prj
        #     mv statistics.shx statistics_${var}_${pgs}m_${region}_${saryears}_${GRID}m_${out_suffix}.shx
        #      ./flux-gate-analysis.py --colormap YlGnBu sequential 4 0 -p small_font --legend long --label_params 'bed_data_set'  -v ${var} --obs_file $obs_dir/$pr_dir/profiles_${pgs}m_${region}_${saryears}_observed_flux_v${ver}.nc $tl_dir/$pr_dir/profiles_${pgs}m_${region}_g${GRID}m_${CLIMATE}_${TYPE}_sia_e_1.25_ppq_0.6_tefo_0.0175_ssa_n_3.0_ssa_e_0.8_philow_5.0_hydro_null_100a.nc ${GRID}m_${CLIMATE}_old_bed/$pr_dir/profiles_${pgs}m_${region}_g${GRID}m_${CLIMATE}_old_bed_e_1.25_ppq_0.6_tefo_0.02_ssa_n_3.25_philow_5.0_hydro_null_100a.nc           
        # done
    done
done
