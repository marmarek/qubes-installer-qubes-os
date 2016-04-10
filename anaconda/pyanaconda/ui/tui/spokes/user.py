# User creation text spoke
#
# Copyright (C) 2013-2014  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#
# Red Hat Author(s): Martin Sivak <msivak@redhat.com>
#                    Chris Lumens <clumens@redhat.com>
#

from pyanaconda.ui.categories.user_settings import UserSettingsCategory
from pyanaconda.ui.tui.spokes import EditTUISpoke
from pyanaconda.ui.tui.spokes import EditTUISpokeEntry as Entry
from pyanaconda.ui.common import FirstbootSpokeMixIn
from pyanaconda.users import guess_username
from pyanaconda.flags import flags
from pyanaconda.i18n import N_, _
from pykickstart.constants import FIRSTBOOT_RECONFIG
from pyanaconda.constants import ANACONDA_ENVIRON, FIRSTBOOT_ENVIRON
from pyanaconda.regexes import GECOS_VALID, USERNAME_VALID, GROUPLIST_SIMPLE_VALID

__all__ = ["UserSpoke"]

class UserSpoke(FirstbootSpokeMixIn, EditTUISpoke):
    """
       .. inheritance-diagram:: UserSpoke
          :parts: 3
    """
    title = N_("User creation")
    category = UserSettingsCategory

    edit_fields = [
        Entry("Create user", "_create", EditTUISpoke.CHECK, True),
        Entry("Username", "name", USERNAME_VALID, lambda self, args: args._create),
        Entry("Use password", "_use_password", EditTUISpoke.CHECK, lambda self, args: args._create),
        Entry("Password", "_password", EditTUISpoke.PASSWORD, lambda self, args: args._use_password and args._create),
        Entry("Groups", "_groups", GROUPLIST_SIMPLE_VALID, lambda self, args: args._create)
        ]

    @classmethod
    def should_run(cls, environment, data):
        # the user spoke should run always in the anaconda and in firstboot only
        # when doing reconfig or if no user has been created in the installation
        if environment == ANACONDA_ENVIRON:
            return True
        elif environment == FIRSTBOOT_ENVIRON and data is None:
            # cannot decide, stay in the game and let another call with data
            # available (will come) decide
            return True
        elif environment == FIRSTBOOT_ENVIRON and data and \
                (data.firstboot.firstboot == FIRSTBOOT_RECONFIG or \
                     len(data.user.userList) == 0):
            return True
        else:
            return False

    def __init__(self, app, data, storage, payload, instclass):
        FirstbootSpokeMixIn.__init__(self)
        EditTUISpoke.__init__(self, app, data, storage, payload, instclass, "user")
        self.dialog.wrong_input_message = _("You have provided an invalid user name.\n"
                                            "Tip: Keep your user name shorter than 32 "
                                            "characters and do not use spaces.\n")

        if self.data.user.userList:
            self.args = self.data.user.userList[0]
            self.args._create = True
        else:
            self.args = self.data.UserData()
            self.args._create = False

        self.args._use_password = self.args.isCrypted or self.args.password

        # Keep the password separate from the kickstart data until apply()
        # so that all of the properties are set at once
        self.args._password = ""

        self.errors = []

    def refresh(self, args=None):
        self.args._groups = ", ".join(self.args.groups)

        # if we have any errors, display them
        while self.errors:
            print(self.errors.pop())

        return EditTUISpoke.refresh(self, args)

    @property
    def completed(self):
        """ Verify a user is created; verify pw is set if option checked. """
        if len(self.data.user.userList) > 0:
            if self.args._use_password and not bool(self.args.password or self.args.isCrypted):
                return False
            else:
                return True
        else:
            return False

    @property
    def showable(self):
        return not (self.completed and flags.automatedInstall
                    and self.data.user.seen and not self.dialog.policy.changesok)

    @property
    def mandatory(self):
        """ Only mandatory if the root pw hasn't been set in the UI
            eg. not mandatory if the root account was locked in a kickstart
        """
        return not self.data.rootpw.password and not self.data.rootpw.lock

    @property
    def status(self):
        if len(self.data.user.userList) == 0:
            return _("No user will be created")
        elif self.args._use_password and not bool(self.args.password or self.args.isCrypted):
            return _("You must set a password")
        elif "wheel" in self.data.user.userList[0].groups:
            return _("Administrator %s will be created") % self.data.user.userList[0].name
        else:
            return _("User %s will be created") % self.data.user.userList[0].name

    def apply(self):
        self.args.groups = [g.strip() for g in self.args._groups.split(",") if g]

        # Add the user to the wheel and qubes groups
        if "wheel" not in self.args.groups:
            self.args.groups.append("wheel")

        if "qubes" not in self.args.groups:
            self.args.groups.append("qubes")

        # Add or remove the user from userlist as needed
        if self.args._create and (self.args not in self.data.user.userList and self.args.name):
            self.data.user.userList.append(self.args)
        elif (not self.args._create) and (self.args in self.data.user.userList):
            self.data.user.userList.remove(self.args)

        # encrypt and store password only if user entered anything; this should
        # preserve passwords set via kickstart
        if self.args._use_password and len(self.args._password) > 0:
            self.args.password = self.args._password
            self.args.isCrypted = True
            self.args.password_kickstarted = False
        # clear pw when user unselects to use pw
        else:
            self.args.password = ""
            self.args.isCrypted = False
            self.args.password_kickstarted = False
