# -*- coding: utf-8 -*-
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2017  Marek Marczykowski-Górecki
#                                   <marmarek@invisiblethingslab.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#


import sys
import re
import langtable
from gi.repository import Gtk, Gdk
import pwquality

from pyanaconda.constants import ANACONDA_ENVIRON

from pyanaconda.ui.gui import GUIObject

from pyanaconda.i18n import _, N_

from pyanaconda.ui.gui.hubs.summary import SummaryHub
from pyanaconda.ui.gui.spokes import StandaloneSpoke
from pyanaconda.ui.gui.spokes.lib.passphrase import PassphraseDialog
from pyanaconda.ui.gui.spokes.lib.passphrase import ERROR_NOT_MATCHING

import logging
log = logging.getLogger("anaconda")

__all__ = ["LUKSPassphraseSpoke"]

class LUKSPassphraseSpoke(StandaloneSpoke):
    builderObjects = ["LUKSPassphraseWindow"]
    mainWidgetName = "LUKSPassphraseWindow"
    uiFile = "spokes/luks_passphrase.glade"

    preForHub = SummaryHub
    priority = 0

    def __init__(self, data, *args, **kwargs):
        super().__init__(data, *args, **kwargs)
        self.passphrase = None
        self.done = False

    @classmethod
    def should_run(cls, environment, data):
        if any(p for p in data.partition.partitions
                if p.encrypted and not p.passphrase):
            return environment == ANACONDA_ENVIRON
        return False

    @property
    def completed(self):
        return (self.passphrase is not None)

    def on_show(self, _arg):
        if not self.done:
            dialog = PassphraseDialog(self.data)
            with self.main_window.enlightbox(dialog.window):
                rc = dialog.run()
            if rc == 1:
                self.passphrase = dialog.passphrase

            self.done = True
            self.window.emit("continue-clicked")

    def apply(self):
        if self.passphrase is None:
            return

        if not self.data.autopart.passphrase:
            self.data.autopart.passphrase = self.passphrase

        for device in self.storage.devices:
            if device.format.type == "luks" and not device.format.exists:
                if not device.format.hasKey:
                    device.format.passphrase = self.passphrase

        for part in self.data.partition.partitions:
            if part.encrypted and not part.passphrase:
                part.passphrase = self.passphrase
