#!/usr/bin/python
# *-* coding: utf-8 *-*
# Author: Thomas Martin <thomas.martin.1@ulaval.ca>
# File: stats.py

## Copyright (c) 2010-2015 Thomas Martin <thomas.martin.1@ulaval.ca>
## 
## This file is part of IRIS
##
## IRIS is free software: you can redistribute it and/or modify it
## under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## IRIS is distributed in the hope that it will be useful, but WITHOUT
## ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
## or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public
## License for more details.
##
## You should have received a copy of the GNU General Public License
## along with IRIS.  If not, see <http://www.gnu.org/licenses/>.

# IMPORT CORE
from orb.core import Tools
from orb.astrometry import Astrometry, StarsParams, Aligner
import orb.utils.image
import orb.data as od
import constants

# OTHER IMPORTS
import math
import os
import numpy as np
import time
import logging
import warnings


class ImageStats(Tools):
    """Compute quality parameters of a SITELLE image.

    Computed parameters are: FWHM of both cameras, sky background,
    extinction, shift along X and Y axis in both cameras.
    """
    image_path = None # Path to SITELLE image
    reffile = None # Reference file instance
    
    im1 = None # image 1
    im2 = None # image 2
    imM = None # merged image
    hdr = None # image header
    dimx = None # image X size
    dimy = None # image Y size
    shape = None # image shape
    star_nb = None # star number
    odometer_nb = None # odometer of the frame

    kwargs = None # Passed keyword arguments
    
    def __init__(self, image_path, force_refresh=False,
                 **kwargs):
        """Init class.

        .. note:: Initialization steps:

           1. (reference image) Compute alignment parameters between
              CAM1 and CAM2
              
           2. Create a merged frame equal to CAM1 + CAM2
        
        :param image_path: Path to a SITELLE raw image.

        :param force_refresh: (Optional) If True the given image is
          considered to be a reference image ad all previous files are
          erased (default False).

        :param kwargs: Keyword arguments of orb.core.Tools class (see
          ORB documentation).      
        """

        kwargs['instrument'] = 'sitelle'

        Tools.__init__(self, **kwargs)
        self.kwargs = kwargs

        self.image_path = image_path

        # check if data needs to be refreshed
        self.refresh = False
        if force_refresh:
            self.refresh = True
        elif not os.path.exists(self._get_reference_file_path()):
            warnings.warn('No reference file created yet. Image taken as reference image.')
            self.refresh = True

        # open reference file
        self.reffile = ReferenceFile(self._get_reference_file_path(),
                                     refresh=self.refresh)


        # read images
        self.im1, self.hdr = self.read_fits(image_path, image_mode='sitelle',
                                            chip_index=1, return_header=True)
        self.im2 = self.read_fits(image_path, image_mode='sitelle',
                                  chip_index=2)
        
        self.dimx = self.im1.shape[0]
        self.dimy = self.im1.shape[1]
        self.shape = self.im1.shape
        
        self.odometer_nb = int(self._get_hdr_keyword('EXPNUM'))

        fov = float(self._get_config_parameter('FIELD_OF_VIEW_1'))
        fwhm_arc = float(self._get_config_parameter('INIT_FWHM'))
        pix_size = float(self._get_config_parameter('PIX_SIZE_CAM1'))
        
        # find alignment parameters if nescessary
        if self.refresh:
            start_time = time.time()
            logging.info('Computing alignment parameters')
            init_angle = float(self._get_config_parameter('INIT_ANGLE'))
            init_dx = float(self._get_config_parameter('INIT_DX'))
            init_dy = float(self._get_config_parameter('INIT_DY'))
            aligner = Aligner(self.im1, self.im2, fwhm_arc, fov, fov, 1, 1,
                              pix_size, pix_size, init_angle, init_dx, init_dy,
                              overwrite=True, **kwargs)
            result = aligner.compute_alignment_parameters(
                correct_distortion=False,
                brute_force=True)

            self.reffile.append('align-params', result['coeffs'])
            self.reffile.append('star-list2', result['star_list2'])
            self.reffile.append('star-list1', result['star_list1'])
            self.reffile.append('fwhm-arc', result['fwhm_arc2'])
            self.reffile.append('rc', result['rc'])
            self.reffile.append('zoom-factor', result['zoom_factor'])
            self.reffile.append('ref-odometer', self.odometer_nb)
            
            logging.info('Alignment parameters ({}) computed  in {:.2f} s'.format(self.reffile.get('align-params'), time.time() - start_time))

        self.astro1 = Astrometry(self.im1, fwhm_arc=fwhm_arc, **kwargs)
        self.astro1.reset_star_list(self.reffile.get('star-list1'))
        self.astro1.reset_fwhm_arc(self.reffile.get('fwhm-arc'))
        self.astro2 = Astrometry(self.im2, fwhm_arc=fwhm_arc, **kwargs)
        self.astro2.reset_star_list(self.reffile.get('star-list2'))
        self.astro2.reset_fwhm_arc(self.reffile.get('fwhm-arc'))


        # creating merged frame
        align_params = self.reffile.get('align-params')
        logging.info('Creating merged frame')
        start_time = time.time()
        self.imM = np.empty_like(self.im1)
        self.imM.fill(np.nan)
        xmin = list() ; ymin = list() ; xmax = list() ; ymax = list()
        
        for istar in range(self.astro1.star_list.shape[0]):
            ix, iy = self.astro1.star_list[istar, :]
            _xmin, _xmax, _ymin, _ymax = orb.utils.image.get_box_coords(
                ix, iy,
                self.astro1.fwhm_pix * 15,
                0, self.dimx, 0, self.dimy)
            xmin.append(_xmin) ; ymin.append(_ymin)
            xmax.append(_xmax) ; ymax.append(_ymax)


        sections = orb.utils.image.transform_frame(
            self.im2,
            xmin, xmax, ymin, ymax,
            self.reffile.get('align-params'),
            self.reffile.get('rc'),
            self.reffile.get('zoom-factor'), 1)

        for isec in range(len(sections)):
            self.imM[xmin[isec]:xmax[isec], ymin[isec]:ymax[isec]] = (
                self.im1[xmin[isec]:xmax[isec], ymin[isec]:ymax[isec]]
                + sections[isec])
            
        logging.info('Merged frame created in {:.2f} s'.format(
            time.time() - start_time))
        
        # init astrometry of merged frame
        self.astroM = Astrometry(self.imM, fwhm_arc=fwhm_arc, **kwargs)
        self.astroM.reset_star_list(self.reffile.get('star-list1'))
        self.astroM.reset_fwhm_arc(self.reffile.get('fwhm-arc'))

        self.star_nb = self.reffile.get('star-list1').shape[0]

      
    def _get_reference_file_path(self):
        """Return the reference file path."""
        return self._data_prefix + 'iris.ref'


    def _get_hdr_keyword(self, key):
        """Return the value of a keyword in the header of the image."""
        if key in self.hdr:
            return self.hdr[key]
        else:
            raise StandardError('Invalid image file the keyword {} must be present.'.format(key))

    def _get_stars_params_group(self, camera, ref=False):
        """Return the hdf5 group of a set of stars parameters given
        the camera number.

        :param camera: Camera number, can be 0, 1 or 2.

        :param ref: (Optional) If True, image is a reference image
          (default False).
        """
        if not ref:
            index = self.odometer_nb
        else:
            index = self.reffile.get('ref-odometer')
            
        if camera == 1 or camera == 2:
            return '{}/cam{}/'.format(index, camera)
        else:
            return '{}/camM/'.format(index)

    def _get_frame_group(self):
        """Return a hdf5 group of the frame based on its odometer number."""
        return '{}'.format(self.odometer_nb)
        


    def compute_stats(self):
        """Compute stats of the image for both cameras."""

        # stars fit
        start_time = time.time()
        logging.info('Fitting_stars in camera 1')
        fit1 = self.astro1.fit_stars_in_frame(0, multi_fit=False,
                                              estimate_local_noise=False,
                                              no_aperture_photometry=True)
        logging.info('Stars fitted in {:.2f} s'.format(
            time.time() - start_time))
        fit1.save_stars_params(self._get_reference_file_path(),
                               self._get_stars_params_group(1))
        
        start_time = time.time()
        logging.info('Fitting_stars in camera 2')
        fit2 = self.astro2.fit_stars_in_frame(0, multi_fit=False,
                                              estimate_local_noise=False,
                                              no_aperture_photometry=True)
        logging.info('Stars fitted in {:.2f} s'.format(
            time.time() - start_time))
        fit2.save_stars_params(self._get_reference_file_path(),
                               self._get_stars_params_group(2))

        start_time = time.time()
        logging.info('Getting star photometry on merged frame')
        fitM = self.astroM.fit_stars_in_frame(0, no_fit=True)
        logging.info('Photometry computed in {:.2f} s'.format(
            time.time() - start_time))
        fitM.save_stars_params(self._get_reference_file_path(),
                               self._get_stars_params_group(0))
        

    def get_stats(self):
        """Return the computed stats in a nice human readable form as
        a dict."""

        def add_data(name, data):
            stats[name] = data.dat
            stats[name + '_err'] = data.err
            
        fit1 = StarsParams(self.star_nb, 1, **self.kwargs)
        fit1.load_stars_params(self._get_reference_file_path(),
                               self._get_stars_params_group(1))
        fit2 = StarsParams(self.star_nb, 1, **self.kwargs)
        fit2.load_stars_params(self._get_reference_file_path(),
                               self._get_stars_params_group(2))
        fitM = StarsParams(self.star_nb, 1, **self.kwargs)
        fitM.load_stars_params(self._get_reference_file_path(),
                               self._get_stars_params_group(0))
        
        fitR1 = StarsParams(self.star_nb, 1, **self.kwargs)
        fitR1.load_stars_params(self._get_reference_file_path(),
                                self._get_stars_params_group(1, ref=True))
        fitR2 = StarsParams(self.star_nb, 1, **self.kwargs)
        fitR2.load_stars_params(self._get_reference_file_path(),
                                self._get_stars_params_group(2, ref=True))
        fitRM = StarsParams(self.star_nb, 1, **self.kwargs)
        fitRM.load_stars_params(self._get_reference_file_path(),
                                self._get_stars_params_group(0, ref=True))
        

        ## compute stats from fit 
        stats = dict()

        # dx 1
        if self.refresh:
            dx1 = od.array(0., np.nanmedian(fit1[:,'x_err']))
        else:
            x1 = od.array(np.nanmedian(fit1[:,'x']), np.nanmedian(fit1[:,'x_err']))
            x1_ref = od.array(np.nanmedian(fitR1[:,'x']), np.nanmedian(fitR1[:,'x_err']))
            dx1 = x1 - x1_ref
        add_data('dx-pix-1', dx1)

        # dx 2
        if self.refresh:
            dx2 = od.array(0., np.nanmedian(fit2[:,'x_err']))
        else:
            x2 = od.array(np.nanmedian(fit2[:,'x']), np.nanmedian(fit2[:,'x_err']))
            x2_ref = od.array(np.nanmedian(fitR2[:,'x']), np.nanmedian(fitR2[:,'x_err']))
            dx2 = x2 - x2_ref
        add_data('dx-pix-2', dx2)

        # dy 1
        if self.refresh:
            dy1 = od.array(0., np.nanmedian(fit1[:,'y_err']))
        else:
            y1 = od.array(np.nanmedian(fit1[:,'y']), np.nanmedian(fit1[:,'y_err']))
            y1_ref = od.array(np.nanmedian(fitR1[:,'y']), np.nanmedian(fitR1[:,'y_err']))
            dy1 = y1 - y1_ref
        add_data('dy-pix-1', dy1)

        # dx 2
        if self.refresh:
            dy2 = od.array(0., np.nanmedian(fit2[:,'y_err']))
        else:
            y2 = od.array(np.nanmedian(fit2[:,'y']), np.nanmedian(fit2[:,'y_err']))
            y2_ref = od.array(np.nanmedian(fitR2[:,'y']), np.nanmedian(fitR2[:,'y_err']))
            dy2 = y2 - y2_ref
        add_data('dy-pix-2', dy2)      
        
        # fwhm 1
        add_data('fwhm-pix-1', od.array(np.nanpercentile(fit1[:, 'fwhm_pix'],10),
                                       	np.nanmedian(fit1[:, 'fwhm_err'])))
        add_data('fwhm-arc-1', od.array(np.nanpercentile(fit1[:, 'fwhm_arc'],10),
          		               	np.nanmedian(fit1[:, 'fwhm_arc_err'])))

        add_data('fwhm-pix-2', od.array(np.nanpercentile(fit2[:, 'fwhm_pix'],10),
                                        np.nanmedian(fit2[:, 'fwhm_err'])))
        add_data('fwhm-arc-2', od.array(np.nanpercentile(fit2[:, 'fwhm_arc'],10),
                                        np.nanmedian(fit2[:, 'fwhm_arc_err'])))
        
        
        # flux
        flux = od.array(np.nanmedian(fitM[:, 'aperture_flux']),
                        np.nanmedian(fitM[:, 'aperture_flux_err']))
        add_data('flux', flux)

        # extinction
        fluxR = od.array(np.nanmedian(fitRM[:, 'aperture_flux']),
                         np.nanmedian(fitRM[:, 'aperture_flux_err']))
        add_data('extinction', -2.5 * od.log10(flux / fluxR))

        # background
        add_data('background', od.array(
            np.nanmedian(fitM[:, 'aperture_background']),
            np.nanmedian(fitM[:, 'aperture_background_err'])))


        stats['odometer_nb'] = self.odometer_nb
        stats['star_nb'] = self.star_nb


        # record stats as attributes
        for key in stats:
            self.reffile.add_attribute(
                self._get_frame_group(), key, stats[key])
        
        return stats
        

class ReferenceFile(Tools):
    """Manage the reference file"""

    def __init__(self, file_path, refresh=False, **kwargs):
        """Init class.

        :param file_path: Path to the reference file

        :param refresh: (Optional) If True, previous reference file is
          erased (default False).

        :param kwargs: kwargs of orb.core.Tools (see ORB
          documentation).
        """

        Tools.__init__(self, **kwargs)

        self.file_path = file_path

        if refresh:
            if os.path.exists(self.file_path):
                os.remove(self.file_path)

    def append(self, dataset, arr):
        """Append a new dataset to the reference file.

        :param dataset: Dataset path
        :param arr: Array to append.
        """
        with self.open_hdf5(self.file_path, 'a') as f:
            if dataset in f:
                del f[dataset]
            f[dataset] = np.array(arr)

    def add_attribute(self, dataset, attr, value):
        """Add an attibute to a dataset

        :param dataset: Dataset path
        :param attr: Attribute name
        :param value: Value of the attribute.
        """
        with self.open_hdf5(self.file_path, 'a') as f:
            f[dataset].attrs[attr] = value

    def get_attributes(self, dataset):
        """Return all the attributes of a dataset as a list of tuples.

        :param dataset: Dataset path.
        """
        with self.open_hdf5(self.file_path, 'r') as f:
            attrs = list()
            for attr in f[dataset].attrs:
                attrs.append((attr, f[dataset].attrs[attr]))
            return attrs
            
    def get(self, dataset, no_error=True):
        """get data of a given dataset.
        
        :param dataset: Dataset path.

        :param no_error: (Optional) If True and if the dataset does
          not exist a vaule of None is returned with no error raised
          (default True).
        """
        with self.open_hdf5(self.file_path, 'r') as f:
             if dataset in f:
                 if f[dataset].size > 1:
                     return f[dataset][:]
                 else:
                     return f[dataset].value
             elif no_error:
                 return None
             else:
                 raise StandardError('{} not in reference file'.format(dataset))

