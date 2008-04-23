#
# Copyright (c) 2006-2008 rPath, Inc.
#
# This program is distributed under the terms of the Common Public License,
# version 1.0. A copy of this license should have been distributed with this
# source file in a file called LICENSE. If it is not present, the license
# is always available at http://www.rpath.com/permanent/licenses/CPL-1.0.
#
# This program is distributed in the hope that it will be useful, but
# without any warranty; without even the implied warranty of merchantability
# or fitness for a particular purpose. See the Common Public License for
# full details.
#

"""
Describes a BuildConfiguration, which is close to, but neither a subset nor
a superset of a conarycfg file.
"""
import os
import urllib2

from conary.lib import cfg,cfgtypes
from conary.conarycfg import ParseError
from conary.lib.cfgtypes import CfgString,CfgPathList,CfgDict

from rmake.build.buildcfg import CfgUser


class rBuildConfiguration(cfg.ConfigFile):
    serverUrl            = CfgString
    user                 = CfgUser
    name                 = CfgString
    contact              = CfgString
    pluginDirs           = (CfgPathList, ['/usr/share/rbuild/plugins',
                                          '~/.rbuild/plugins.d'])
    rmakeUrl             = CfgString
    repositoryMap        = CfgDict(CfgString)

    def __init__(self, readConfigFiles=False, ignoreErrors=False, root=''):
        cfg.ConfigFile.__init__(self)
        if hasattr(self, 'setIgnoreErrors'):
            self.setIgnoreErrors(ignoreErrors)
        if readConfigFiles:
            self.readFiles(root=root)

    def validateServerUrl(self):
        urllib2.urlopen(self.serverUrl).read(1024)

    def readFiles(self, root=''):
        self.read(root + '/etc/rbuildrc', exception=False)
        if os.environ.has_key("HOME"):
            self.read(root + os.environ["HOME"] + "/" + ".rbuildrc",
                      exception=False)
        self.read('rbuildrc', exception=False)

    def getRbuilderHost(self):
        return urllib2.splithost(urllib2.splittype(self.serverUrl)[1])[0]

    def getRmakeUrl(self):
        if not self.rmakeUrl:
            return 'https://%s:9999' % self.getRbuilderHost()
        return self.rmakeUrl
