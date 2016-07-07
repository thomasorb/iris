#!/usr/bin/python
# *-* coding: utf-8 *-*
# Author: Thomas Martin <thomas.martin.1@ulaval.ca>
# File: iris.py

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

from orb.core import Tools, OutHDFCube, HDFCube
from stats import ImageStats
import numpy as np
import os

class Iris(Tools):
    """Interface class between the user and
    :py:class:`iris.stats.ImageStats`

    This class is called by **scripts/iris**
    """

    imstats = None # ImageStats instance
    
    def __init__(self, image_path, force_refresh=False,
                 daemon_port=None, **kwargs):
        """Init class.

        :param image_path: Path to the SITELLE image.

        :param force_refresh: (Optional) If True the given image is
          considered to be a reference image ad all previous files are
          erased (default False).

        :param kwargs: Keyword arguments of orb.core.Tools class (see
          ORB documentation).

        :param daemon_port: Listening port of the viewer daemon.
        """

        kwargs['config_file_name'] = 'config.sitelle.orb'

        Tools.__init__(self, **kwargs)


        self.imstats = ImageStats(image_path, force_refresh=force_refresh,
                                  **kwargs)
        

        # construct data cube
        if self.imstats.refresh:
            reset = True
            overwrite = False
            new_dimz = 1
            frame_index = 0
            
        else:
            reset = False
            overwrite = True
            out1 = HDFCube(self._get_outcube_path(1))
            # check if odometer already exists
            frame_index = out1.dimz
            new_dimz = out1.dimz + 1
            for iframe in range(out1.dimz):
                if self.imstats.odometer_nb == out1.get_frame_attribute(
                    iframe, 'odometer_nb'):
                    frame_index = iframe
                    new_dimz = out1.dimz
            
            del out1

        
        out1 = OutHDFCube(self._get_outcube_path(1),
                          (self.imstats.dimx, self.imstats.dimy, new_dimz),
                          reset=reset, overwrite=overwrite)
        out2 = OutHDFCube(self._get_outcube_path(2),
                          (self.imstats.dimx, self.imstats.dimy, new_dimz),
                          reset=reset, overwrite=overwrite)
        outM = OutHDFCube(self._get_outcube_path(0),
                          (self.imstats.dimx, self.imstats.dimy, new_dimz),
                          reset=reset, overwrite=overwrite)
            
        out1.write_frame(frame_index, data=self.imstats.im1)
        out1.write_frame_attribute(
            frame_index, 'odometer_nb', self.imstats.odometer_nb)
        
        out2.write_frame(frame_index, data=self.imstats.im2)
        out2.write_frame_attribute(
            frame_index, 'odometer_nb', self.imstats.odometer_nb)
       
        outM.write_frame(frame_index, data=self.imstats.imM)
        outM.write_frame_attribute(
            frame_index, 'odometer_nb', self.imstats.odometer_nb)
       


    def _get_outcube_path(self, camera, absolute=False):
        """Return the path to the ouput cube.

        :param camera: Camera number. May be 0, 1 or 2.
        :param absolute: If True, return absolute path.
        """
        if camera == 1 or camera == 2:
            path = self._data_prefix + 'cube.{}.hdf5'.format(camera)
        elif camera == 0:
            path = self._data_prefix + 'cube.m.hdf5'
        else:
            self._print_error('camera must be 0, 1 or 2.')
        if absolute:
            return os.path.abspath(path)
        else:
            return path


    def run_stats(self):
        """Run statistics computation."""
        self.imstats.compute_stats()
        return self.imstats.get_stats()
        
