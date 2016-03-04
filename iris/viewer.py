#!/usr/bin/python
# *-* coding: utf-8 *-*
# Author: Thomas Martin <thomas.martin.1@ulaval.ca> 
# File: gui.py

## Copyright (c) 2010-2014 Thomas Martin <thomas.martin.1@ulaval.ca>
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


from orb.viewer import BaseViewer, ZPlotWindow
import socket
import threading
import gtk
import os
from orb.core import HDFCube
from orb.astrometry import StarsParams
from stats import ReferenceFile


class IrisViewer(BaseViewer):
    """Iris Viewer class."""

    daemon = None # IRIS daemon instance
    daemon_port = None # Communication port of the daemon
    _lock = False
    
    iris_reffile_path = None # reference file path
    iris_all_stats = None # iris stats of all frames

    stat_window = None # stat window


    def _toggle_lock_cb(self, c):
        self._lock = ~self._lock
        if self._lock:
            c.set_label('Unlock')
        else:
            c.set_label('Lock')
    
    def _get_hplugins(self):
        """Create plugins to add to the base viewer."""
        control_frame = gtk.Frame('IRIS Controls')
        control_framebox = gtk.VBox(spacing=3)

        # Controls
        controlsbox = gtk.HBox()
        lockbutton = gtk.Button('Lock')
        lockbutton.connect('clicked', self._toggle_lock_cb)
        refreshbutton = gtk.Button('Refresh')
        refreshbutton.connect('clicked', self._update_iris_cb)
        controlsbox.pack_start(lockbutton)
        controlsbox.pack_start(refreshbutton)
        control_framebox.pack_start(controlsbox, fill=True, expand=False)
        
        # Change camera
        rbutton_box = gtk.VBox()
        rbutton1 = gtk.RadioButton(label='Camera 1')
        rbutton2 = gtk.RadioButton(group=rbutton1, label='Camera 2')
        rbutton0 = gtk.RadioButton(group=rbutton1, label='Merged cube')
        for rbutton in [rbutton1, rbutton2, rbutton0]:
            rbutton.connect('clicked', self._camera_changed_cb)
            rbutton_box.pack_start(rbutton)
        control_framebox.pack_start(rbutton_box, fill=True, expand=False)

        # Display stats
        statsbox = gtk.VBox()
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self.stats_store = gtk.ListStore(str, str, str)
        stats_tv = gtk.TreeView(self.stats_store)
        stats_tv.connect('cursor-changed', self._get_selected_stat)
        key_render = gtk.CellRendererText()
        key_render.set_property('font', 'mono')
        key_render.set_property('size-points', 10)
        key_render.set_property('editable', True)
        key_render.set_property('weight', 800)
        
        value_render =  gtk.CellRendererText()
        value_render.set_property('font', 'mono')
        value_render.set_property('size-points', 10)
        value_render.set_property('editable', True)

        
        col_key = gtk.TreeViewColumn("Key", key_render, text=0)
        col_value = gtk.TreeViewColumn("Value", value_render, text=1)
        col_err = gtk.TreeViewColumn("Error", value_render, text=2)
      
        stats_tv.append_column(col_key)
        stats_tv.append_column(col_value)
        stats_tv.append_column(col_err)

        stats_tv.set_size_request(200,-1)
        sw.add(stats_tv)
        statsbox.pack_start(sw, fill=True, expand=True)

        control_framebox.pack_start(statsbox, fill=True, expand=True)
        control_frame.add(control_framebox)

        self._add_plugins_postload_call(self._postload_call)
        return [control_frame]

    def _start_listener_daemon(self, daemon_port=9000):
        """Launch a socket listener daemon to enable communication
        with the viewer from external processes.

        :param daemon_port: Listening port of the daemon.

        .. note:: If nescessary the listener may be stopped by sending the message 'stop', e.g.:
        
            .. code-block:: python
            
              import socket
              s = socket.socket(socket.AF_INET,
                                socket.SOCK_STREAM)
              s.connect((socket.gethostname(), port))
              s.send('stop'.encode('ascii'))
              s.close()    
        """
        def _listen():
            stop = False
            while not stop:
                # establish connection with client socket
                clientSocket, addr = s.accept()
                msg = clientSocket.recv(1024).decode('ascii')
                print ' > message from {}: {}'.format(addr, msg)
                if 'update' in msg:
                    path = msg.split()[1]
                    print ' > filepath: ', path
                    if os.path.abspath(path) == os.path.abspath(
                        self.filepath):
                        if not self._lock:
                            self._reload_file()
                    else:
                        self.load_file(path)
                elif msg == 'stop':
                    stop = True
                clientSocket.close()
            print ' > daemon listener stopped'

        self.daemon_port = daemon_port
        s = socket.socket(socket.AF_INET,
                          socket.SOCK_STREAM)
        s.bind((socket.gethostname(), self.daemon_port))
        s.listen(5)
        self.daemon = threading.Thread(target=_listen)
        self.daemon.daemon = True
        self.daemon.start()

    def _update_iris_cb(self, c):
        """update-callback Reload data cube.

        :param c: Caller instance.
        """
        self.iris_all_stats = None
        if not self._lock:
            self._reload_file()

    def _get_selected_stat(self, c):
        """stat-selection-callback.

        :param c: Caller instance.
        """
        selection = c.get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        tree_model, tree_iter = selection.get_selected()
        selected_stat = tree_model.get_value(tree_iter, 0)
        self.update_all_stats()
        zdata = self.iris_all_stats[0,:,selected_stat]
        if self.stat_window is None:
            self.stat_window = ZPlotWindow(None, None, None, None,
                                           title='Stats', simple=True)
            self.stat_window.show()
        elif not self.stat_window.w.get_property('visible'):
            self.stat_window = ZPlotWindow(None, None, None, None,
                                           title='Stats', simple=True)
            self.stat_window.show()
            
        self.stat_window.update(zdata, ylabel=selected_stat)

    def _set_image_index_cb(self, c):
        """set-image-index-callback.

        Called when a new image index is choosen.

        :param c: Caller instance.
        """
        self.update_stats_store(int(c.get_value()))
        BaseViewer._set_image_index_cb(self, c)
        
    def _camera_changed_cb(self, c):
        """camera-changed-callback.

        Called when a new camera to display is choosen.

        :param c: Caller instance.
        """
        
        label = c.get_label()
        fileroot = os.path.splitext(os.path.splitext(self.filepath)[0])[0]

        if label == 'Camera 1':
            filepath = fileroot + '.1.hdf5'
        elif label == 'Camera 2':
            filepath = fileroot + '.2.hdf5'
        elif label == 'Merged cube':
            filepath = fileroot + '.m.hdf5'
        else:
            raise ValueError('Unknown button label')
                        
        if filepath != self.filepath:
            self.load_file(filepath)

    def _postload_call(self):
        """Function called immediatly after a cube as been loaded"""
        
        self.wimage_index.set_value(self.dimz - 1)
        self.update_all_stats()
        self.update_stats_store(self.dimz - 1)

    def update_all_stats(self):
        """Load all the statistics of all the frames."""
        
        self.iris_reffile_path = os.path.join(
            os.path.split(self.filepath)[0], 'iris.ref')
        reffile = ReferenceFile(self.iris_reffile_path)
        
        iris_all_stats = StarsParams(1, self.cube.shape[2])
        
        cube = HDFCube(self.filepath)
        for iframe in range(self.cube.dimz):
            frame_stats = None
            if self.iris_all_stats is not None:
                if iframe < self.iris_all_stats.frame_nb:
                    if self.iris_all_stats[0, iframe] != {}:
                        frame_stats = self.iris_all_stats[0, iframe]
                        
            if frame_stats is None:
                try:
                    odometer_nb = cube.get_frame_attribute(
                        iframe, 'odometer_nb')
                    stats = reffile.get_attributes('{}'.format(odometer_nb))
                    frame_stats = dict()
                    for istat in stats:
                        frame_stats[istat[0]] = istat[1]
                except Exception, e:
                    print 'Error: {}'.format(e)

            if frame_stats is not None:
                iris_all_stats[0, iframe] = frame_stats
                
        self.iris_all_stats = iris_all_stats
                
        del reffile
                
            
    def update_stats_store(self, index):
        """Update displayed statistics."""
        self.stats_store.clear()
        if self.iris_all_stats is not None:
            if self.iris_all_stats.frame_nb > index:
                stats = self.iris_all_stats[:,index][0]
                for istat in stats:
                    if '_err' not in istat:
                        key = istat
                        if isinstance(stats[key], float):
                            val = '{:.2f}'.format(stats[key])
                        else:
                            val = '{}'.format(stats[key])
                        if key + '_err' in stats:
                            if isinstance(stats[ key + '_err'], float):
                                err = '{:.2f}'.format(stats[ key + '_err'])
                            else:
                                err = '{}'.format(stats[ key + '_err'])

                        else:
                            err = ''
                        self.stats_store.append([
                             key, val, err])

        
