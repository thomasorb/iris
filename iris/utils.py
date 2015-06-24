#!/usr/bin/python
# *-* coding: utf-8 *-*
# Author: Thomas Martin <thomas.martin.1@ulaval.ca>
# File: utils.py

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

import socket

def send_msg_to_daemon(msg, port):
    """Send a message to the listener daemon created by iris-viewer.
    
    :param msg: Message to send
    :param port: Listening port
    """
    try:
        s = socket.socket(socket.AF_INET,
                          socket.SOCK_STREAM)
        s.connect((socket.gethostname(), port))
        s.send(msg.encode('ascii'))
        s.close()
    except Exception, e:
        print 'Error on sending {} to listener daemon on port {}: {}'.format(
            msg, port, e)
