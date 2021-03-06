#!/usr/bin/env python

# Copyright (C) 2017 Andy Aschwanden

from argparse import ArgumentParser
import matplotlib.transforms as transforms
from matplotlib.ticker import FormatStrFormatter
from netCDF4 import Dataset as NC

import matplotlib as mpl
import matplotlib.cm as cmx

from cdo import Cdo
cdo = Cdo()

import cf_units
import numpy as np
import pandas as pa
import pylab as plt
import ogr

try:
    from pypismtools import unit_converter, smooth
except:
    from pypismtools.pypismtools import unit_converter, smooth

basin_list = ['CW', 'NE', 'NO', 'NW', 'SE', 'SW']
rcp_list = ['26', '45', '85']

# Set up the option parser
parser = ArgumentParser()
parser.description = "A script for PISM output files to time series plots using pylab/matplotlib."
parser.add_argument("FILE", nargs='*')
parser.add_argument("--bounds", dest="bounds", nargs=2, type=float,
                    help="lower and upper bound for ordinate, eg. -1 1", default=None)
parser.add_argument("--time_bounds", dest="time_bounds", nargs=2, type=float,
                    help="lower and upper bound for abscissa, eg. 1990 2000", default=[2008, 3008])
parser.add_argument("-b", "--basin", dest="basin",
                    choices=basin_list,
                    help="Basin to plot", default='GRIS')
parser.add_argument("-l", "--labels", dest="labels",
                    help="comma-separated list with labels, put in quotes like 'label 1,label 2'", default=None)
parser.add_argument("-f", "--output_format", dest="out_formats",
                    help="Comma-separated list with output graphics suffix, default = pdf", default='pdf')
parser.add_argument("-n", "--parallel_threads", dest="openmp_n",
                    help="Number of OpenMP threads for operators such as enssstat, Default=1", default=1)
parser.add_argument("--no_legends", dest="do_legend", action="store_false",
                    help="Do not plot legend",
                    default=True)
parser.add_argument("-o", "--output_file", dest="outfile",
                    help="output file name without suffix, i.e. ts_control -> ts_control_variable", default='unnamed')
parser.add_argument("--step", dest="step", type=int,
                    help="step for plotting values, if time-series is very long", default=1)
parser.add_argument("--start_year", dest="start_year", type=float,
                    help='''Start year''', default=2008)
parser.add_argument("--rcp", dest="mrcp",
                    choices=rcp_list,
                    help="Which RCP", default=26)
parser.add_argument("--rotate_xticks", dest="rotate_xticks", action="store_true",
                    help="rotate x-ticks by 30 degrees, Default=False",
                    default=False)
parser.add_argument("-r", "--output_resolution", dest="out_res",
                    help='''Resolution ofoutput graphics in dots per
                  inch (DPI), default = 300''', default=300)
parser.add_argument("--runmean", dest="runmean", type=int,
                    help='''Calculate running mean''', default=None)
parser.add_argument("-t", "--twinx", dest="twinx", action="store_true",
                    help='''adds a second ordinate with units mmSLE,
                  Default=False''', default=False)
parser.add_argument("--plot", dest="plot",
                    help='''What to plot.''',
                    choices=['basin_mass',
                             'basin_d',
                             'per_basin_flux',
                             'per_basin_d',
                             'rcp_mass',
                             'rcp_accum',
                             'rcp_runoff',
                             'rcp_d',
                             'rcp_flux',
                             'rcp_fluxes',
                             'rcp_traj'],
                    default='rcp_mass')
parser.add_argument("--title", dest="title",
                    help='''Plot title.''', default=None)
parser.add_argument("--ctrl_file", dest="ctrl_file", nargs='*',
                    help='''Filename of ctrl run''', default=None)

options = parser.parse_args()
basin = options.basin
mrcp = options.mrcp
ifiles = options.FILE
if options.labels != None:
    labels = options.labels.split(',')
else:
    labels = None
bounds = options.bounds
do_legend = options.do_legend
runmean = options.runmean
time_bounds = options.time_bounds
openmp_n = options.openmp_n
out_res = options.out_res
outfile = options.outfile
out_formats = options.out_formats.split(',')
plot = options.plot
rotate_xticks = options.rotate_xticks
step = options.step
title = options.title
twinx = options.twinx
ctrl_file = options.ctrl_file
dashes = ['-', '--', '-.', ':', '-', '--', '-.', ':']

if openmp_n > 1:
    pthreads = '-P {}'.format(openmp_n)
else:
    pthreads = ''

dx, dy = 4. / out_res, -4. / out_res

# Conversion between giga tons (Gt) and millimeter sea-level equivalent (mmSLE)
gt2mmSLE = 1. / 365
gt2cmSLE = 1. / 365 / 10.
gt2mSLE = 1. / 365 / 1000.

start_year = options.start_year

# Plotting styles
shadow_color = '0.25'
numpoints = 1

fontsize = 6
lw = 0.5
aspect_ratio = 0.35
markersize = 2
fig_width = 3.15  # inch
fig_height = aspect_ratio * fig_width  # inch
fig_size = [fig_width, fig_height]

params = {'backend': 'ps',
          'axes.linewidth': 0.25,
          'lines.linewidth': lw,
          'axes.labelsize': fontsize,
          'font.size': fontsize,
          'xtick.direction': 'in',
          'xtick.labelsize': fontsize,
          'xtick.major.size': 2.5,
          'xtick.major.width': 0.25,
          'ytick.direction': 'in',
          'ytick.labelsize': fontsize,
          'ytick.major.size': 2.5,
          'ytick.major.width': 0.25,
          'legend.fontsize': fontsize,
          'lines.markersize': markersize,
          'font.size': fontsize,
          'figure.figsize': fig_size}

plt.rcParams.update(params)


basin_col_dict = {'SW': '#542788',
                  'CW': '#b35806',
                  'NE': '#e08214',
                  'NO': '#fdb863',
                  'NW': '#b2abd2',
                  'SE': '#8073ac',
                  'GR': '#000000'}

rcp_col_dict = {'CTRL': 'k',
                '85': '#d94701',
                '45': '#fd8d3c',
                '26': '#fdbe85'}

rcp_dict = {'26': 'RCP 2.6',
            '45': 'RCP 4.5',
            '85': 'RCP 8.5',
            'CTRL': 'CTRL'}

flux_to_mass_vars_dict = {'tendency_of_ice_mass_glacierized': 'ice_mass',
             'tendency_of_ice_mass_due_to_flow': 'flow_cumulative',
             'tendency_of_ice_mass_due_to_conservation_error': 'conservation_error_cumulative',
             'tendency_of_ice_mass_due_to_basal_mass_flux': 'basal_mass_flux_cumulative',
             'tendency_of_ice_mass_due_to_surface_mass_flux': 'surface_mass_flux_cumulative',
             'tendency_of_ice_mass_due_to_discharge': 'discharge_cumulative'}
flux_vars = flux_to_mass_vars_dict.keys()

flux_abbr_dict = {'tendency_of_ice_mass_glacierized': '$\dot \mathregular{M}$',
                  'tendency_of_ice_mass': '$\dot \mathregular{M}$',
                  'tendency_of_ice_mass_due_to_flow': 'divQ',
                  'tendency_of_ice_mass_due_to_conservation_error': '\dot e',
                  'tendency_of_ice_mass_due_to_basal_mass_flux': 'BMB',
                  'tendency_of_ice_mass_due_to_surface_mass_flux': 'SMB',
                  'tendency_of_ice_mass_due_to_discharge': 'D',
                  'discharge_flux': 'D'}

flux_short_dict = {'tendency_of_ice_mass_glacierized': 'dmdt',
                  'tendency_of_ice_mass_due_to_flow': 'divq',
                  'tendency_of_ice_mass_due_to_conservation_error': 'e',
                  'tendency_of_ice_mass_due_to_basal_mass_flux': 'bmb',
                  'tendency_of_ice_mass_due_to_surface_mass_flux': 'smb',
                  'tendency_of_ice_mass_due_to_discharge': 'd'}


flux_style_dict = {'tendency_of_ice_mass': '-',
                   'tendency_of_ice_mass_due_to_flow': ':',
                   'tendency_of_ice_mass_due_to_conservation_error': ':',
                   'tendency_of_ice_mass_due_to_basal_mass_flux': '-.',
                   'tendency_of_ice_mass_due_to_surface_mass_flux': ':',
                   'tendency_of_ice_mass_due_to_discharge': '--',
                   'discharge': '--',
                   'discharge_flux': '--',
                   'surface_accumulation_rate': ':',
                   'surface_runoff_rate': '-.'}

mass_abbr_dict = {'ice_mass': 'M',
             'flow_cumulative': 'Q',
             'conservation_error_cumulative': 'e',
             'basal_mass_flux_cumulative': 'BMB',
             'surface_mass_flux_cumulative': 'SMB',
             'discharge_cumulative': 'D'}

mass_style_dict = {'ice_mass': '-',
             'flow_cumulative': ':',
             'conservation_error_cumulative': ':',
             'basal_mass_flux_cumulative': '-.',
             'surface_mass_flux_cumulative': ':',
             'discharge_cumulative': '--'}

flux_plot_vars = ['surface_accumulation_rate', 'surface_runoff_rate', 'surface_melt_rate', 'tendency_of_ice_mass_due_to_discharge', 'tendency_of_ice_mass_due_to_surface_mass_balance']
mass_plot_vars = ['ice_mass']

flux_ounits = 'Gt year-1'
mass_ounits = 'Gt'

runmean_window = 11

lhs_params_dict = {'FICE': {'param_name': 'surface.pdd.factor_ice', 'vmin': 4, 'vmax': 12, 'scale_factor': 910, 'symb': '$f_{\mathregular{i}}$'},
                   'FSNOW': {'param_name': 'surface.pdd.factor_snow', 'vmin': 2, 'vmax': 6, 'scale_factor': 910, 'symb': '$f_{\mathregular{s}}$'},
                   'PRS': {'param_name': 'atmosphere.precip_exponential_factor_for_temperature', 'vmin': 5, 'vmax': 7, 'scale_factor': 100, 'symb': '$\omega$'},
                   'RFR': {'param_name': 'surface.pdd.refreeze', 'vmin': 25, 'vmax': 75, 'scale_factor': 100, 'symb': '$\psi$'}
}



def plot_rcp_mass(plot_var=mass_plot_vars):
    
    fig = plt.figure()
    offset = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
    ax = fig.add_subplot(111)

    for k, rcp in enumerate(rcp_list[::-1]):

        rcp_files = [f for f in ifiles if 'rcp_{}'.format(rcp) in f]
        if len(rcp_files) < 3:
            
            print('Less than 3 files found for {}, skipping'.format(rcp_dict[rcp]))

        else:

            print('Reading files for {}'.format(rcp_dict[rcp]))
            
            cdf_enspctl16 = cdo.enspctl('16',input=rcp_files, returnCdf=True, options=pthreads)
            cdf_enspctl84 = cdo.enspctl('84',input=rcp_files, returnCdf=True, options=pthreads)
            cdf_ensmedian = cdo.enspctl('50', input=rcp_files, returnCdf=True, options=pthreads)
            t = cdf_ensmedian.variables['time'][:]

            enspctl16_vals = cdf_enspctl16.variables[plot_var][:] - cdf_enspctl16.variables[plot_var][0]
            iunits = cdf_enspctl16[plot_var].units
            enspctl16_vals = -unit_converter(enspctl16_vals, iunits, mass_ounits) * gt2mSLE

            enspctl84_vals = cdf_enspctl84.variables[plot_var][:] - cdf_enspctl84.variables[plot_var][0]
            iunits = cdf_enspctl84[plot_var].units
            enspctl84_vals = -unit_converter(enspctl84_vals, iunits, mass_ounits) * gt2mSLE

            ensmedian_vals = cdf_ensmedian.variables[plot_var][:] - cdf_ensmedian.variables[plot_var][0]
            iunits = cdf_ensmedian[plot_var].units
            ensmedian_vals = -unit_converter(ensmedian_vals, iunits, mass_ounits) * gt2mSLE

            date = np.arange(start_year + step,
                             start_year + (len(t[:]) + 1) * step,
                             step) 


            # ensemble between 16th and 84th quantile
            ax.fill_between(date[:], enspctl16_vals, enspctl84_vals,
                            color=rcp_col_dict[rcp],
                            alpha=0.5,
                            linewidth=0)

            ax.plot(date[:], ensmedian_vals,
                            color=rcp_col_dict[rcp],
                            linewidth=0.5,
                            label=rcp_dict[rcp])

            ax.plot(date[:], enspctl16_vals,
                    color=rcp_col_dict[rcp],
                    linestyle='solid',
                    linewidth=0.25)

            ax.plot(date[:], enspctl84_vals,
                    color=rcp_col_dict[rcp],
                    linestyle='solid',
                    linewidth=0.25)

            if ctrl_file is not None:
                rcp_ctrl_file = [f for f in ctrl_file if 'rcp_{}'.format(rcp) in f][0]
                    
                cdf_ctrl = cdo.readCdf(rcp_ctrl_file)
                ctrl_t = cdf_ctrl.variables['time'][:]
                cdf_date = np.arange(start_year + step,
                                 start_year + (len(ctrl_t[:]) + 1) * step,
                                 step) 
                
                ctrl_vals = cdf_ctrl.variables[plot_var][:] - cdf_ctrl.variables[plot_var][0]
                iunits = cdf_ctrl[plot_var].units
                ctrl_vals = -unit_converter(ctrl_vals, iunits, mass_ounits) * gt2mSLE
                ax.plot(cdf_date[:], ctrl_vals,
                        color=rcp_col_dict[rcp],
                        linestyle='dashed',
                        linewidth=0.5)
                

            for m_year in [2100, 2200, 2500, 3000]:
                idx = np.where(np.array(date) == m_year)[0][0]
                m_median = ensmedian_vals[idx]
                m_pctl16 = enspctl16_vals[idx]
                m_pctl84 = enspctl84_vals[idx]
                m_ctrl = ctrl_vals[idx]
                print('Year {}: {:1.2f} - {:1.2f} - {:1.2f} m SLE'.format(m_year, m_pctl84, m_median, m_pctl16))
                print('         CTRL {:1.2f} m SLE'.format(m_ctrl))


    if do_legend:
        legend = ax.legend(loc="upper right",
                           edgecolor='0',
                           bbox_to_anchor=(0, 0, .35, 0.88),
                           bbox_transform=plt.gcf().transFigure)
        legend.get_frame().set_linewidth(0.0)
    
    ax.set_xlabel('Year (CE)')
    ax.set_ylabel('$\Delta$(GMSL) (m)')
        
    if time_bounds:
        ax.set_xlim(time_bounds[0], time_bounds[1])

    if bounds:
        ax.set_ylim(bounds[0], bounds[1])

    ymin, ymax = ax.get_ylim()

    ax.yaxis.set_major_formatter(FormatStrFormatter('%1.2f'))

    if rotate_xticks:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
                tick.set_rotation(30)
    else:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
            tick.set_rotation(0)
                    
    if title is not None:
            plt.title(title)

    for out_format in out_formats:
        out_file = outfile + '_rcp' + '_'  + plot_var + '.' + out_format
        print "  - writing image %s ..." % out_file
        fig.savefig(out_file, bbox_inches='tight', dpi=out_res)

        
def plot_rcp_flux(plot_var=flux_plot_vars):
    
    fig = plt.figure()
    offset = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
    ax = fig.add_subplot(111)
    
    for k, rcp in enumerate(rcp_list[::-1]):

        rcp_files = [f for f in ifiles if 'rcp_{}'.format(rcp) in f]
        if len(rcp_files) < 3:
            
            print('Less than 3 files found for {}, skipping'.format(rcp_dict[rcp]))

        else:

            print('Reading files for {}'.format(rcp_dict[rcp]))
            
            cdf_enspctl16 = cdo.enspctl('16',input=rcp_files, options=pthreads)
            cdf_enspctl16 = cdo.runmean('11',input=cdf_enspctl16, returnCdf=True, options=pthreads)
            cdf_enspctl84 = cdo.enspctl('84',input=rcp_files, options=pthreads)
            cdf_enspctl84 = cdo.runmean('11',input=cdf_enspctl84, returnCdf=True, options=pthreads)
            cdf_ensmedian = cdo.enspctl('50', input=rcp_files, options=pthreads)
            cdf_ensmedian = cdo.runmean('11',input=cdf_ensmedian, returnCdf=True, options=pthreads)
            t = cdf_ensmedian.variables['time'][:]

            enspctl16_vals = cdf_enspctl16.variables[plot_var][:]
            iunits = cdf_enspctl16[plot_var].units
            enspctl16_vals = -unit_converter(enspctl16_vals, iunits, flux_ounits) * gt2cmSLE

            enspctl84_vals = cdf_enspctl84.variables[plot_var][:]
            iunits = cdf_enspctl84[plot_var].units
            enspctl84_vals = -unit_converter(enspctl84_vals, iunits, flux_ounits) * gt2cmSLE
            
            ensmedian_vals = cdf_ensmedian.variables[plot_var][:]
            iunits = cdf_ensmedian[plot_var].units
            ensmedian_vals = -unit_converter(ensmedian_vals, iunits, flux_ounits) * gt2cmSLE

            date = np.arange(start_year + step,
                             start_year + (len(t[:]) + 1) * step,
                             step) 


            # ensemble between 16th and 84th quantile
            ax.fill_between(date[:], enspctl16_vals, enspctl84_vals,
                            color=rcp_col_dict[rcp],
                            alpha=0.5,
                            linewidth=0)

            ax.plot(date[:], ensmedian_vals,
                    color=rcp_col_dict[rcp],
                    linewidth=0.5,
                    label=rcp_dict[rcp])

            ax.plot(date[:], enspctl16_vals,
                    color=rcp_col_dict[rcp],
                    linestyle='solid',
                    linewidth=0.25)

            ax.plot(date[:], enspctl84_vals,
                    color=rcp_col_dict[rcp],
                    linestyle='solid',
                    linewidth=0.25)

            if ctrl_file is not None:
                rcp_ctrl_file = [f for f in ctrl_file if 'rcp_{}'.format(rcp) in f][0]
                
                cdf_ctrl = cdo.runmean('11', input=rcp_ctrl_file, returnCdf=True, options=pthreads)
                ctrl_t = cdf_ctrl.variables['time'][:]
                cdf_date = np.arange(start_year + step,
                                     start_year + (len(ctrl_t[:]) + 1) * step, step) 
                
                ctrl_vals = cdf_ctrl.variables[plot_var][:]
                iunits = cdf_ctrl[plot_var].units
                ctrl_vals = -unit_converter(ctrl_vals, iunits, flux_ounits) * gt2cmSLE
                ax.plot(cdf_date[:], ctrl_vals,
                        color=rcp_col_dict[rcp],
                        linestyle='dashed',
                        linewidth=0.5)
                

            for m_year in [2100, 2200, 2500]:
                idx = np.where(np.array(date) == m_year)[0][0]
                m_median = ensmedian_vals[idx]
                m_pctl16 = enspctl16_vals[idx]
                m_pctl84 = enspctl84_vals[idx]
                print('Year {}: {:1.2f} - {:1.2f} - {:1.2f} cm SLE year-1'.format(m_year, m_pctl84, m_median, m_pctl16))


    if do_legend:
        legend = ax.legend(loc="upper right",
                           edgecolor='0',
                           bbox_to_anchor=(0, 0, .35, 0.88),
                           bbox_transform=plt.gcf().transFigure)
        legend.get_frame().set_linewidth(0.0)
    
    ax.set_xlabel('Year (CE)')
    ax.set_ylabel('rate of GMSL rise (cm yr$^{\mathregular{-1}}$)')
        
    if time_bounds:
        ax.set_xlim(time_bounds[0], time_bounds[1])

    if bounds:
        ax.set_ylim(bounds[0], bounds[1])

    ymin, ymax = ax.get_ylim()

    ax.yaxis.set_major_formatter(FormatStrFormatter('%1.2f'))

    if rotate_xticks:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
                tick.set_rotation(30)
    else:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
            tick.set_rotation(0)
                    
    if title is not None:
            plt.title(title)

    for out_format in out_formats:
        out_file = outfile + '_rcp' + '_'  + plot_var + '.' + out_format
        print "  - writing image %s ..." % out_file
        fig.savefig(out_file, bbox_inches='tight', dpi=out_res)


def plot_rcp_flux_gt(plot_var=flux_plot_vars, anomaly=False):
    
    fig = plt.figure()
    offset = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
    ax = fig.add_subplot(111)
    
    for k, rcp in enumerate(rcp_list[::-1]):

        rcp_files = [f for f in ifiles if 'rcp_{}'.format(rcp) in f]
        if len(rcp_files) < 3:
            
            print('Less than 3 files found for {}, skipping'.format(rcp_dict[rcp]))

        else:

            print('Reading {} for {}'.format(plot_var, rcp_dict[rcp]))

            cdf_enspctl16 = cdo.enspctl('16',input=rcp_files, options=pthreads)
            cdf_enspctl84 = cdo.enspctl('84',input=rcp_files, options=pthreads)
            cdf_ensmedian = cdo.enspctl('50', input=rcp_files, options=pthreads)
            t = cdf_ensmedian.variables['time'][:]
            
            if anomaly == True:
                cdf_enspctl16 = cdo.runmean('11', input='-sub {} -timmean -selyear,2008/2018 {}'.format(cdf_enspctl16, cdf_enspctl16), returnCdf=True, options=pthreads)
                cdf_enspctl84 = cdo.runmean('11', input='-sub {} -timmean -selyear,2008/2018 {}'.format(cdf_enspctl84, cdf_enspctl84), returnCdf=True, options=pthreads)
                cdf_ensmedian = cdo.runmean('11', input='-sub {} -timmean -selyear,2008/2018 {}'.format(cdf_ensmeadian, cdf_ensmedian), returnCdf=True, options=pthreads)
            else:
                cdf_enspctl16 = cdo.runmean('11', input=cdf_enspctl16, returnCdf=True, options=pthreads)
                cdf_enspctl84 = cdo.runmean('11', input=cdf_enspctl84, returnCdf=True, options=pthreads)
                cdf_ensmedian = cdo.runmean('11', input=cdf_ensmeadian, returnCdf=True, options=pthreads)

                
            enspctl16_vals = cdf_enspctl16.variables[plot_var][:]
            iunits = cdf_enspctl16[plot_var].units
            enspctl16_vals = unit_converter(enspctl16_vals, iunits, flux_ounits)

            enspctl84_vals = cdf_enspctl84.variables[plot_var][:]
            iunits = cdf_enspctl84[plot_var].units
            enspctl84_vals = unit_converter(enspctl84_vals, iunits, flux_ounits)
            
            ensmedian_vals = cdf_ensmedian.variables[plot_var][:]
            iunits = cdf_ensmedian[plot_var].units
            ensmedian_vals = unit_converter(ensmedian_vals, iunits, flux_ounits)

            date = np.arange(start_year + step,
                             start_year + (len(t[:]) + 1) * step,
                             step) 


            # ensemble between 16th and 84th quantile
            ax.fill_between(date[:], enspctl16_vals, enspctl84_vals,
                            color=rcp_col_dict[rcp],
                            alpha=0.4,
                            linewidth=0)

            ax.plot(date[:], ensmedian_vals,
                    color=rcp_col_dict[rcp],
                    linewidth=0.5,
                    label=rcp_dict[rcp])

            ax.plot(date[:], enspctl16_vals,
                    color=rcp_col_dict[rcp],
                    linestyle='solid',
                    linewidth=0.25)

            ax.plot(date[:], enspctl84_vals,
                    color=rcp_col_dict[rcp],
                    linestyle='solid',
                    linewidth=0.25)

            if ctrl_file is not None:
                rcp_ctrl_file = [f for f in ctrl_file if 'rcp_{}'.format(rcp) in f][0]
                
                cdf_ctrl = cdo.readCdf(rcp_ctrl_file)
                ctrl_t = cdf_ctrl.variables['time'][:]
                cdf_date = np.arange(start_year + step,
                                     start_year + (len(ctrl_t[:]) + 1) * step, step) 
                
                ctrl_vals = cdf_ctrl.variables[plot_var][:] - cdf_ctrl.variables[plot_var][0]
                iunits = cdf_ctrl[plot_var].units
                ctrl_vals = unit_converter(ctrl_vals, iunits, ounits)
                ax.plot(cdf_date[:], ctrl_vals,
                        color=rcp_col_dict[rcp],
                        linestyle='dashed',
                        linewidth=0.5)
                

            for m_year in [2100, 2200, 2500]:
                idx = np.where(np.array(date) == m_year)[0][0]
                m_median = ensmedian_vals[idx]
                m_pctl16 = enspctl16_vals[idx]
                m_pctl84 = enspctl84_vals[idx]
                print('Year {}: {:1.2f} - {:1.2f} - {:1.2f} Gt year-1'.format(m_year, m_pctl84, m_median, m_pctl16))
                if ctrl_file:
                    m_ctrl = ctrl_vals[idx]
                    print('     CTRL    {:1.2f} Gt year-1'.format(m_ctrl))


    if do_legend:
        legend = ax.legend(loc="upper right",
                           edgecolor='0',
                           bbox_to_anchor=(0, 0, .35, 0.88),
                           bbox_transform=plt.gcf().transFigure)
        legend.get_frame().set_linewidth(0.0)
    
    ax.set_xlabel('Year (CE)')
    ax.set_ylabel('flux (Gt/yr)')
        
    if time_bounds:
        ax.set_xlim(time_bounds[0], time_bounds[1])

    if bounds:
        ax.set_ylim(bounds[0], bounds[1])

    ymin, ymax = ax.get_ylim()

    ax.yaxis.set_major_formatter(FormatStrFormatter('%1.0f'))

    if rotate_xticks:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
                tick.set_rotation(30)
    else:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
            tick.set_rotation(0)
                    
    if title is not None:
            plt.title(title)

    for out_format in out_formats:
        out_file = outfile + '_rcp' + '_'  + plot_var + '.' + out_format
        print "  - writing image %s ..." % out_file
        fig.savefig(out_file, bbox_inches='tight', dpi=out_res)

def plot_rcp_flux_cumulative(plot_var=flux_plot_vars):
    
    fig = plt.figure()
    offset = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
    ax = fig.add_subplot(111)
    
    for k, rcp in enumerate(rcp_list):

        rcp_files = [f for f in ifiles if 'rcp_{}'.format(rcp) in f]
        if len(rcp_files) < 3:
            
            print('Less than 3 files found for {}, skipping'.format(rcp_dict[rcp]))

        else:

            print('Reading files for {}'.format(rcp_dict[rcp]))
            
            cdf_enspctl16 = cdo.enspctl('16',input=rcp_files, options=pthreads)
            cdf_enspctl16 = cdo.timcumsum(input=cdf_enspctl16, returnCdf=True, options=pthreads)
            cdf_enspctl84 = cdo.enspctl('84',input=rcp_files, options=pthreads)
            cdf_enspctl84 = cdo.timcumsum(input=cdf_enspctl84, returnCdf=True, options=pthreads)
            cdf_ensmedian = cdo.enspctl('50', input=rcp_files, options=pthreads)
            cdf_ensmedian = cdo.timcumsum(input=cdf_ensmedian, returnCdf=True, options=pthreads)
            t = cdf_ensmedian.variables['time'][:]

            enspctl16_vals = cdf_enspctl16.variables[plot_var][:]
            iunits = cdf_enspctl16[plot_var].units
            iunits_cf = cf_units.Unit(iunits) * cf_units.Unit('yr')
            o_units_cf = cf_units.Unit(mass_ounits)
            enspctl16_vals = iunits_cf.convert(enspctl16_vals, o_units_cf) * gt2mSLE

            enspctl84_vals = cdf_enspctl84.variables[plot_var][:]
            iunits = cdf_enspctl84[plot_var].units
            iunits_cf = cf_units.Unit(iunits) * cf_units.Unit('yr')
            o_units_cf = cf_units.Unit(mass_ounits)
            enspctl84_vals = iunits_cf.convert(enspctl84_vals, o_units_cf) * gt2mSLE
            
            ensmedian_vals = cdf_ensmedian.variables[plot_var][:]
            iunits = cdf_ensmedian[plot_var].units
            iunits_cf = cf_units.Unit(iunits) * cf_units.Unit('yr')
            o_units_cf = cf_units.Unit(mass_ounits)
            ensmedian_vals = iunits_cf.convert(ensmedian_vals, o_units_cf) * gt2mSLE
            
            date = np.arange(start_year + step,
                             start_year + (len(t[:]) + 1) * step,
                             step) 


            # ensemble between 16th and 84th quantile
            ax.fill_between(date[:], enspctl16_vals, enspctl84_vals,
                            color=rcp_col_dict[rcp],
                            alpha=0.5,
                            linewidth=0)

            ax.plot(date[:], ensmedian_vals,
                    color=rcp_col_dict[rcp],
                    linewidth=0.5,
                    label=rcp_dict[rcp])

            ax.plot(date[:], enspctl16_vals,
                    color=rcp_col_dict[rcp],
                    linestyle='solid',
                    linewidth=0.25)

            ax.plot(date[:], enspctl84_vals,
                    color=rcp_col_dict[rcp],
                    linestyle='solid',
                    linewidth=0.25)

            for m_year in [2100, 2200, 2500]:
                idx = np.where(np.array(date) == m_year)[0][0]
                m_median = ensmedian_vals[idx]
                m_pctl16 = enspctl16_vals[idx]
                m_pctl84 = enspctl84_vals[idx]
                print('Year {}: {:1.2f} - {:1.2f} - {:1.2f} cm SLE year-1'.format(m_year, m_pctl84, m_median, m_pctl16))


    if do_legend:
        legend = ax.legend(loc="upper right",
                           edgecolor='0',
                           bbox_to_anchor=(0, 0, .35, 0.88),
                           bbox_transform=plt.gcf().transFigure)
        legend.get_frame().set_linewidth(0.0)
    
    ax.set_xlabel('Year (CE)')
    ax.set_ylabel('$\Delta$(GMSL) (cm/yr)')
        
    if time_bounds:
        ax.set_xlim(time_bounds[0], time_bounds[1])

    if bounds:
        ax.set_ylim(bounds[0], bounds[1])

    ymin, ymax = ax.get_ylim()

    ax.yaxis.set_major_formatter(FormatStrFormatter('%1.2f'))

    if rotate_xticks:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
                tick.set_rotation(30)
    else:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
            tick.set_rotation(0)
                    
    if title is not None:
            plt.title(title)

    for out_format in out_formats:
        out_file = outfile + '_rcp' + '_'  + plot_var + '.' + out_format
        print "  - writing image %s ..." % out_file
        fig.savefig(out_file, bbox_inches='tight', dpi=out_res)

        
def plot_rcp_traj_mass(plot_var=mass_plot_vars):

    jet = cm = plt.get_cmap('jet')
    
    for k, rcp in enumerate(rcp_list):

        rcp_files = [f for f in ifiles if 'rcp_{}'.format(rcp) in f]

        if len(rcp_files) < 3:
            
            print('Less than 3 files found for {}, skipping'.format(rcp_dict[rcp]))

        else:

            print('Reading files for {}'.format(rcp_dict[rcp]))

            cdf_mass_enspctl16 = cdo.enspctl('16',input=rcp_files, returnCdf=True, options=pthreads)
            cdf_mass_enspctl84 = cdo.enspctl('84',input=rcp_files, returnCdf=True, options=pthreads)
            cdf_mass_ensmedian = cdo.enspctl('50', input=rcp_files, returnCdf=True, options=pthreads)
            t = cdf_mass_ensmedian.variables['time'][:]

            mass_enspctl16_vals = cdf_mass_enspctl16.variables[plot_var][:] - cdf_mass_enspctl16.variables[plot_var][0]
            iunits = cdf_mass_enspctl16[plot_var].units
            mass_enspctl16_vals = -unit_converter(mass_enspctl16_vals, iunits, mass_ounits) * gt2mSLE

            mass_enspctl84_vals = cdf_mass_enspctl84.variables[plot_var][:] - cdf_mass_enspctl84.variables[plot_var][0]
            iunits = cdf_mass_enspctl84[plot_var].units
            mass_enspctl84_vals = -unit_converter(mass_enspctl84_vals, iunits, mass_ounits) * gt2mSLE

            mass_ensmedian_vals = cdf_mass_ensmedian.variables[plot_var][:] - cdf_mass_ensmedian.variables[plot_var][0]
            iunits = cdf_mass_ensmedian[plot_var].units
            mass_ensmedian_vals = -unit_converter(mass_ensmedian_vals, iunits, mass_ounits) * gt2mSLE

            date = np.arange(start_year + step,
                             start_year + (len(t[:]) + 1) * step,
                             step) 

            for lhs_param in lhs_params_dict:
                param = lhs_params_dict[lhs_param]
                param_name = param['param_name']
                param_scale_factor = param['scale_factor']
                norm = mpl.colors.Normalize(vmin=param['vmin'], vmax=param['vmax'])
                scalarMap = cmx.ScalarMappable(norm=norm, cmap=jet)

                fig = plt.figure()
                offset = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
                ax = fig.add_subplot(111)

                for rcp_file in rcp_files:
                    nc = NC(rcp_file, 'r')
                    pism_config = nc.variables['pism_config']
                    param_value = getattr(pism_config, param_name) * param_scale_factor
                    colorVal = scalarMap.to_rgba(param_value)

                    cdf_rcp_mass_file = nc.variables[plot_var]
                    mass_vals =  nc.variables[plot_var][:] - nc.variables[plot_var][0]
                    iunits = cdf_rcp_mass_file.units
                    mass_vals = -unit_converter(mass_vals, iunits, mass_ounits) * gt2mSLE
                    ax.plot(date[:], mass_vals,
                            alpha=0.3,
                            linewidth=0.2,
                            color=colorVal)
                    nc.close()

                    ax.plot(date[:], mass_ensmedian_vals,
                            color='k',
                            linewidth=0.5)

                    ax.plot(date[:], mass_enspctl16_vals,
                            color='k',
                            linestyle='dashed',
                            linewidth=0.25)

                    ax.plot(date[:], mass_enspctl84_vals,
                            color='k',
                            linestyle='dashed',
                            linewidth=0.25)

                    idx = np.where(np.array(date) == time_bounds[-1])[0][0]
                    m_median = mass_ensmedian_vals[idx]
                    m_pctl16 = mass_enspctl16_vals[idx]
                    m_pctl84 = mass_enspctl84_vals[idx]


                    # x_sle, y_sle = time_bounds[-1], m_median
                    # plt.text( x_sle, y_sle, '{: 1.2f}$\pm${:1.2f}'.format(m_median, m_diff),
                    #           color='k')

                    # if do_legend:
                    #     legend = ax.legend(loc="upper right",
                    #                        edgecolor='0',
                    #                        bbox_to_anchor=(0, 0, .35, 0.88),
                    #                        bbox_transform=plt.gcf().transFigure)
                    #     legend.get_frame().set_linewidth(0.0)

                    ax.set_xlabel('Year (CE)')
                    ax.set_ylabel('$\Delta$(GMSL) (m)')

                    if time_bounds:
                        ax.set_xlim(time_bounds[0], time_bounds[1])

                    if bounds:
                        ax.set_ylim(bounds[0], bounds[1])

                    ymin, ymax = ax.get_ylim()

                    ax.yaxis.set_major_formatter(FormatStrFormatter('%1.2f'))

                    if rotate_xticks:
                        ticklabels = ax.get_xticklabels()
                        for tick in ticklabels:
                            tick.set_rotation(30)
                    else:
                        ticklabels = ax.get_xticklabels()
                        for tick in ticklabels:
                            tick.set_rotation(0)

                    title = '{} {}'.format(rcp_dict[rcp], lhs_params_dict[lhs_param]['symb'])
                    if title is not None:
                        plt.title(title)

                for out_format in out_formats:
                    out_file = outfile + '_rcp' + '_'  + rcp + '_' + lhs_param.lower() + '_' + plot_var + '.' + out_format
                    print "  - writing image %s ..." % out_file
                    fig.savefig(out_file, bbox_inches='tight', dpi=out_res)


def plot_basin_mass():
    
    fig = plt.figure()
    offset = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
    ax = fig.add_subplot(111)

    mass_var_vals_positive_cum = 0
    mass_var_vals_negative_cum = 0
    for k, ifile in enumerate(ifiles):
        basin = basin_list[k]
        print('reading {}'.format(ifile))
        nc = NC(ifile, 'r')
        t = nc.variables["time"][:]

        date = np.arange(start_year + step,
                         start_year + (len(t[:]) + 1) * step,
                         step) 

        idx = np.where(np.array(date) == time_bounds[-1])[0][0]
        mvar = 'ice_mass'
        mass_var_vals = -np.squeeze(nc.variables[mvar][:] - nc.variables[mvar][0]) * gt2mSLE
        iunits = nc.variables[mvar].units
        mass_var_vals = unit_converter(mass_var_vals, iunits, mass_ounits)
        if mass_var_vals[idx] > 0:
            ax.fill_between(date[:], mass_var_vals_positive_cum, mass_var_vals_positive_cum + mass_var_vals[:],
                            color=basin_col_dict[basin],
                            linewidth=0,
                            label=basin)
        else:
            print mass_var_vals[idx]
            ax.fill_between(date[:], mass_var_vals_negative_cum, mass_var_vals_negative_cum + mass_var_vals[:],
                            color=basin_col_dict[basin],
                            linewidth=0,
                            label=basin)
            plt.rcParams['hatch.color'] = basin_col_dict[basin]
            plt.rcParams['hatch.linewidth'] = 0.1
            ax.fill_between(date[:], mass_var_vals_negative_cum, mass_var_vals_negative_cum + mass_var_vals[:],
                            facecolor="none", hatch="XXXXX", edgecolor="k",
                            linewidth=0.0)

        if mass_var_vals[idx] > 0:
            ax.plot(date[:], mass_var_vals_positive_cum + mass_var_vals[:],
                    color='k',
                    linewidth=0.1)
        else:
            ax.plot(date[:], mass_var_vals_negative_cum + mass_var_vals[:],
                    color='k',
                    linewidth=0.1)

        offset = 0
        if mass_var_vals[idx] > 0:
            try:
                x_sle, y_sle = date[idx] + offset, mass_var_vals_positive_cum[idx]
            except:  # first iteratio
                x_sle, y_sle = date[idx] + offset, mass_var_vals_positive_cum
        else:
            try:
                x_sle, y_sle = date[idx] + offset, mass_var_vals_negative_cum[idx] + mass_var_vals[idx] 
            except:  # first iteration
                x_sle, y_sle = date[idx] + offset, mass_var_vals_negative_cum + mass_var_vals[idx] 
        nc.close()
        if mass_var_vals[idx] > 0:
            mass_var_vals_positive_cum += mass_var_vals
        else:
            mass_var_vals_negative_cum += mass_var_vals

    ax.hlines(0, time_bounds[0], time_bounds[-1], lw=0.25)

    legend = ax.legend(loc="upper right",
                       edgecolor='0',
                       bbox_to_anchor=(0, 0, 1.15, 1),
                       bbox_transform=plt.gcf().transFigure)
    legend.get_frame().set_linewidth(0.2)
    
    ax.set_xlabel('Year (CE)')
    ax.set_ylabel('$\Delta$(GMSL) (m)')
        
    if time_bounds:
        ax.set_xlim(time_bounds[0], time_bounds[1])

    if bounds:
        ax.set_ylim(bounds[0], bounds[-1])

    if rotate_xticks:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
                tick.set_rotation(30)
    else:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
            tick.set_rotation(0)
                    
    if title is not None:
            plt.title(title)

    for out_format in out_formats:
        out_file = outfile + '_' + mvar  + '.' + out_format
        print "  - writing image %s ..." % out_file
        fig.savefig(out_file, bbox_inches='tight', dpi=out_res)  
 
def plot_basin_flux(plot_var='discharge'):
    '''
    Make a plot per basin with all flux_plot_vars
    '''

    fig = plt.figure()
    offset = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
    ax = fig.add_subplot(111)

    for basin in basin_list:

        basin_file = [f for f in ifiles if 'b_{}'.format(basin) in f]
        print basin_file

        print('reading {}'.format(basin_file[0]))

        if plot_var == 'discharge':
            cdf = cdo.expr('discharge=tendency_of_ice_mass_due_to_discharge+tendency_of_ice_mass_due_to_basal_mass_flux', input=basin_file[0])
            cdf_run = cdo.runmean('11', input=cdf, returnCdf=True, options=pthreads)
        
            iunits = 'Gt year-1'
            var_vals = cdf_run.variables[plot_var][:]

        t = cdf_run.variables["time"][:]

        date = np.arange(start_year + step,
                         start_year + (len(t[:]) + 1) * step,
                         step) 


        var_vals = unit_converter(np.squeeze(var_vals), iunits, flux_ounits)
        plt.plot(date[:], var_vals[:],
                 color=basin_col_dict[basin],
                 lw=0.5)

    if do_legend:
        legend = ax.legend(loc="upper right",
                           edgecolor='0',
                           bbox_to_anchor=(0, 0, 1.15, 1),
                           bbox_transform=plt.gcf().transFigure)
        legend.get_frame().set_linewidth(0.2)
    
    ax.set_xlabel('Year (CE)')
    ax.set_ylabel('mass flux (Gt yr$^{\mathregular{-1}}$)')
        
    if time_bounds:
        ax.set_xlim(time_bounds[0], time_bounds[1])
            
    if bounds:
        ax.set_ylim(bounds[0], bounds[1])

    if rotate_xticks:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
            tick.set_rotation(30)
    else:
        ticklabels = ax.get_xticklabels()
        for tick in ticklabels:
            tick.set_rotation(0)
                    
    if title is not None:
        plt.title(title)

    for out_format in out_formats:
        out_file = outfile  + '_fluxes.' + out_format
        print "  - writing image %s ..." % out_file
        fig.savefig(out_file, bbox_inches='tight', dpi=out_res)
                   

def plot_per_basin_flux(plot_var=None):
    '''
    Make a plot per basin with all flux_plot_vars
    '''

    for basin in basin_list:

        fig = plt.figure()
        offset = transforms.ScaledTranslation(dx, dy, fig.dpi_scale_trans)
        ax = fig.add_subplot(111)

        basin_file = [f for f in ifiles if 'b_{}'.format(basin) in f]

        for k, rcp in enumerate(rcp_list[::-1]):
            rcp_file = [f for f in basin_file if 'rcp_{}'.format(rcp) in f]

            print('reading {}'.format(rcp_file[0]))

            cdf_run = cdo.runmean('11', input=rcp_file[0], returnCdf=True, options=pthreads)
            t = cdf_run.variables["time"][:]
            date = np.arange(start_year + step,
                             start_year + (len(t[:]) + 1) * step,
                             step) 

            if plot_var is None:
                m_vars = ['tendency_of_ice_mass_due_to_surface_mass_flux',
                          'tendency_of_ice_mass_due_to_discharge']
                label_var = 'fluxes'
            else:
                m_vars = [plot_var]
                label_var = plot_var
                
            for m_var in m_vars:

                iunits = cdf_run.variables[m_var].units
                var_vals = cdf_run.variables[m_var][:]

                var_vals = unit_converter(np.squeeze(var_vals), iunits, flux_ounits)
                plt.plot(date[:], var_vals[:],
                         color=rcp_col_dict[rcp],
                         ls=flux_style_dict[m_var],
                         lw=0.5)

        if do_legend:
            legend = ax.legend(loc="upper right",
                               edgecolor='0',
                               bbox_to_anchor=(0, 0, 1.15, 1),
                               bbox_transform=plt.gcf().transFigure)
            legend.get_frame().set_linewidth(0.2)
    
        ax.set_xlabel('Year (CE)')
        ax.set_ylabel('mass flux (Gt yr$^{\mathregular{-1}}$)')
        
        if time_bounds:
            ax.set_xlim(time_bounds[0], time_bounds[1])
            
        if bounds:
            ax.set_ylim(bounds[0], bounds[1])

        if rotate_xticks:
            ticklabels = ax.get_xticklabels()
            for tick in ticklabels:
                tick.set_rotation(30)
        else:
            ticklabels = ax.get_xticklabels()
            for tick in ticklabels:
                tick.set_rotation(0)
                    
        if title is not None:
            plt.title(title)

        for out_format in out_formats:
            out_file = outfile  + '_' + basin + '_' + label_var + '.' + out_format
            print "  - writing image %s ..." % out_file
            fig.savefig(out_file, bbox_inches='tight', dpi=out_res)
                   
if plot == 'rcp_mass':
    plot_rcp_mass(plot_var='limnsw')
elif plot == 'rcp_flux':
    plot_rcp_flux(plot_var='tendency_of_ice_mass_glacierized')
elif plot == 'rcp_fluxes':
    for plot_var in flux_plot_vars:
        plot_rcp_flux_gt(plot_var=plot_var)
elif plot == 'rcp_accum':
    plot_rcp_flux_cumulative(plot_var='surface_accumulation_rate')
elif plot == 'rcp_d':
    plot_rcp_flux_cumulative(plot_var='tendency_of_ice_mass_due_to_discharge')
elif plot == 'rcp_traj':
    plot_rcp_traj_mass(plot_var='limnsw')
elif plot == 'basin_mass':
    plot_basin_mass()
elif plot == 'basin_d':
    plot_basin_flux(plot_var='discharge')
elif plot == 'per_basin_flux':
    plot_per_basin_flux()
elif plot == 'per_basin_d':
    plot_per_basin_flux(plot_var='discharge_flux')
