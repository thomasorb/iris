#!/usr/bin/python
# *-* coding: utf-8 *-*
# Author: Thomas Martin <thomas.martin.1@ulaval.ca>
# File: image.py

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


import os


DATA_PREFIX = '.iris' + os.sep
"""Data path prefix"""

KEY_LIST = ('odometer_nb', 'star_nb','fwhm-arc-1', 'fwhm-arc-1_err',
            'fwhm-arc-2', 'fwhm-arc-2_err', 'extinction', 'extinction_err',
            'background', 'background_err', 'dx-pix-1', 'dx-pix-1_err',
            'dy-pix-1', 'dy-pix-1_err', 'dx-pix-2', 'dx-pix-2_err',
            'dy-pix-2', 'dy-pix-2_err')
"""List of the parameters printed on stdout"""
