.. Orbs documentation master file, created by
   sphinx-quickstart on Sat May 26 01:02:35 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


IRIS Documentation
##################

.. image:: images/logo.*
   :width: 25%
   :align: center

.. topic:: Welcome to IRIS documentation !
   
  **IRIS** (*Interface Rapide d'Information et de Synthèse pour*
  SITELLE_) is a software built to analyze quickly raw observing
  frames of SITELLE_ and help the observer to check their quality as
  soon as they are obtained.

  .. _SITELLE: 

  **SITELLE** (Spectromètre-Imageur pour l’Étude en Long et en Large
  des raie d’Émissions) is a larger version of SpIOMM operating at the
  CFHT_ (Canada-France-Hawaii Telescope, Hawaii, USA).

Table of contents
-----------------

.. contents::




IRIS Guide
----------

You will find here what you need to know to reduce your data. This is
also certainly the first place to look if you experience any problem
using ORBS.

.. toctree::
   :maxdepth: 2

   guide


Code Documentation
------------------

The code documentation can help you understand how the whole reduction
process works in details.

.. toctree::
   :maxdepth: 2

   iris_module
   stats_module
   utils_module
   viewer_module
   constants_module

Changelog
---------

.. toctree::
   :maxdepth: 2

   changelog

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. _Mégantic: http://omm.craq-astro.ca/
.. _CFHT: http://www.cfht.hawaii.edu/
.. _Python: http://www.python.org/
.. _Scipy: http://www.scipy.org/
.. _Numpy: http://numpy.scipy.org/
.. _PyFITS: http://www.stsci.edu/resources/software_hardware/pyfits
.. _Parallel: http://www.parallelpython.com/
