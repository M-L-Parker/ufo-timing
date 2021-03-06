#!/usr/bin/env python

import numpy as np
import matplotlib.pyplot as pl
from ufo_functions import *
import roman
import os


run_settings=settings('halibut_settings.txt')
elements=run_settings.elements
densities=run_settings.densities
lc_filename=run_settings.lightcurve
clobber=run_settings.clobber

# elements=['Fe','Si','S','Ne', 'Mg', 'Ar','Ca']

# Load lightcurve
# lc_filename='example_lightcurve.lc'
test_lightcurve=lightcurve(lc_filename)
for interval in run_settings.cut_intervals:
	test_lightcurve.cut_interval(interval[0],interval[1])
if run_settings.rebin is not None:
	test_lightcurve.rebin(run_settings.rebin)
test_lightcurve.filter_null()

# Define time resolution, resample lightcurve
resample_factor=run_settings.resample # higher number = smaller time bins 
lc_spline=test_lightcurve.spline()
manual_times=np.linspace(min(test_lightcurve.time),max(test_lightcurve.time),resample_factor*len(test_lightcurve.time))
time_resolution=float(max(manual_times)-min(manual_times))/float(len(manual_times))

# Mean ionization - 10^3 seems reasonable...
mean_countrate=test_lightcurve.mean
mean_xi=run_settings.xi
densities=run_settings.densities #Units of 10^20 m^-3


initial_countrate=test_lightcurve.countrate[0]
initial_xi=calc_xi_from_countrate(initial_countrate,mean_countrate,mean_xi)
print '\nInitial count rate:',initial_countrate
print 'Initial ionization:',initial_xi

toolbar_width=60
for density in densities:
	print '\nRunning calculations for density',density
		# Load rates and equilibrium concentrations
	concentrations=pion_concentrations(density=density)
	rates=pion_rates(density=density)

	for element in elements:

		output_dir='time_dependent_ions'
		lightcurve_stem=''.join(lc_filename.split('.')[:-1])
		outfilename='ion_concs_'+lightcurve_stem+'_'+element+'_'+str(density)+'.npz'
		if not os.path.exists(output_dir+'/'+outfilename) or clobber:

			print '\nCalculating time-dependent ion concentrations for',element


			# Load rates and equilibrium concentrations
			ions=rates.get_ions(element)

			true_density=density*1.e20
			print '\nRunning solver:'
			print '\tDensity:',true_density,'m^-3'
			print '\tElement:',element
			print 'Sampling every',time_resolution,'seconds:'

			# Get intial ion concentrations
			initial_concs=concentrations.get_concentrations(element, ions, initial_xi)
			current_concs=initial_concs

			time_dependent_concentrations=[]
			ionization_rates=[]
			recombination_rates=[]

			xi_values=[]


			for t_step, countrate in zip(range(0,len(manual_times)), lc_spline(manual_times)):
				time=manual_times[t_step]

				### This needs modifying to not run every step. I can't be bothered now.
				toolbar_update(float(t_step)/float(len(manual_times)),toolbar_width)

				if t_step != len(manual_times)-1:
					delta_t=manual_times[t_step+1]-time

					current_xi=calc_xi_from_countrate(countrate, mean_countrate, mean_xi)
					xi_values.append(current_xi)

					### This function needs upgrading to a better iterative method. See above.
					net_rates, temp_i_rates, temp_r_rates = rates.get_net_rates(element, np.log10(current_xi), ions, current_concs)

					current_concs=current_concs+net_rates*delta_t

					time_dependent_concentrations.append(current_concs)
					ionization_rates.append(temp_i_rates)
					recombination_rates.append(temp_r_rates)
			toolbar_update(1,toolbar_width)

			print '\nDone.'

			# Final time-dependent ion concentrations array for element. Axis 0 is time, axis 1 ion number
			time_dependent_concentrations=np.array(time_dependent_concentrations)
			ionization_rates=np.array(ionization_rates)
			recombination_rates = np.array(recombination_rates)

			print '\nSaving ion concentrations:'
			if not os.path.exists(output_dir):
				print '\tPath',output_dir,'does not exist, making folder'
				os.mkdir(output_dir)
			if os.path.exists(output_dir+'/'+outfilename):
				print '\tFile',outfilename,'already exists, deleting'
				os.remove(output_dir+'/'+outfilename)
			np.savez(output_dir+'/'+outfilename, times=manual_times, concentrations=time_dependent_concentrations,\
					ionizations=xi_values, lightcurve=lc_spline(manual_times),ionization_rates=ionization_rates,\
					recombination_rates=recombination_rates)
			print '\tSaved as',outfilename

print '\nCalculations complete.'
print '\tTo view output, use output_analyser.py'
print '\tTo fake models based on these calculations, use generate_models.py'