#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Python motu client
#
# Motu, a high efficient, robust and Standard compliant Web Server for Geographic
#  Data Dissemination.
# 
#  http://cls-motu.sourceforge.net/
# 
#  (C) Copyright 2009-2010, by CLS (Collecte Localisation Satellites) -
#  http://www.cls.fr - and Contributors
# 
# 
#  This library is free software; you can redistribute it and/or modify it
#  under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation; either version 2.1 of the License, or
#  (at your option) any later version.
# 
#  This library is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
#  or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
#  License for more details.
# 
#  You should have received a copy of the GNU Lesser General Public License
#  along with this library; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

import os

_messages = None

MESSAGES_FILE = './messages.properties'


def get_external_messages():
    """Return a table of externalized messages.
        
    The table is lazzy instancied (loaded once when called the first time)."""
    global _messages
    if _messages is None:
        with open(os.path.join(os.path.dirname(__file__), MESSAGES_FILE), "rU") as propFile:
            prop_dict = dict()
            for propLine in propFile:
                prop_def = propLine.strip()
                if len(prop_def) == 0:
                    continue
                if prop_def[0] in ('!', '#'):
                    continue
                punctuation = [prop_def.find(c) for c in ':= '] + [len(prop_def)]
                found = min([pos for pos in punctuation if pos != -1])
                name = prop_def[:found].rstrip()
                value = prop_def[found:].lstrip(":= ").rstrip()
                prop_dict[name] = value
            _messages = prop_dict
    return _messages
