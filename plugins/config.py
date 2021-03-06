#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import os

from rbuild import constants
from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command

class ConfigCommand(command.BaseCommand):
    commands = ['config']
    help = 'Print the rbuild configuration'
    docs = {
        'ask': '(Re)run interactive config questionaire;'
               ' write all configuration files',
        'conaryrc': 'Re-write ~/.conaryrc-rbuild',
        'rmakerc': 'Re-write ~/.rmakerc-rbuild',
    }

    # configuration setup is not required to run the help command
    requireConfig = False

    def addLocalParameters(self, argSet):
        argSet['ask'] = command.NO_PARAM
        argSet['conaryrc'] = command.NO_PARAM
        argSet['rmakerc'] = command.NO_PARAM

    def runCommand(self, handle, argSet, _):
        writeConaryrc = argSet.pop('conaryrc', False)
        writeRmakerc = argSet.pop('rmakerc', False)
        if argSet.pop('ask', False):
            handle.Config.updateConfig()
        elif writeConaryrc or writeRmakerc:
            # if --ask, then updateConfig already called these
            if writeConaryrc:
                handle.Config.writeConaryConfiguration()
            if writeRmakerc:
                handle.Config.writeRmakeConfiguration()
        else:
            handle.Config.displayConfig()


def _requiresHome(func):
    def wrapper(*args, **kw):
        'Decorator for methods that require HOME env variable to be set'
        if 'HOME' in os.environ:
            if not os.path.isdir(os.environ['HOME']):
                raise errors.PluginError('The HOME environment variable references'
                                         ' "%s" which does not exist')
            return func(*args, **kw)
        raise errors.PluginError('The HOME environment variable must be set')
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


class Config(pluginapi.Plugin):
    name = 'config'

    def registerCommands(self):
        self.handle.Commands.registerCommand(ConfigCommand)

    def displayConfig(self, hidePasswords=True, prettyPrint=True):
        """
        Display the current build configuration for this helper.

        @param hidePasswords: If C{True} (default), display C{<password>}
        instead of the literal password in the output.
        @param prettyPrint: If C{True} (default), print output in
        human-readable format that may not be parsable by a config reader.
        If C{False}, the configuration output should be valid as input.
        """
        cfg = self.handle.getConfig()
        cfg.setDisplayOptions(hidePasswords=hidePasswords,
                              prettyPrint=prettyPrint)
        cfg.display()

    @staticmethod
    def isComplete(cfg):
        for cfgItem in ['serverUrl', 'name', 'contact', 'user']:
            if not cfg[cfgItem]:
                return False
        return True

    @_requiresHome
    def initializeConfig(self, cfg=None):
        if cfg is None:
            cfg = self.handle.getConfig()
        ui = self.handle.ui
        ui.write('''\
********************************************************
Welcome to rBuild!  Your configuration is incomplete.
Please answer the following questions to begin using rBuild:
''')

        self.updateConfig(cfg)

        ui.write("rBuild configuration complete.  To rerun this"
                 " configuration test run rbuild config --ask,"
                 " or simply edit ~/.rbuildrc.")
        ui.write('')
        ui.write("You should now begin working with a product by running"
                   " 'rbuild init <short name> <version>'")

    def getServerUrl(self, defaultUrl):
        ui = self.handle.ui
        validateUrl = self.handle.facade.rbuilder.validateUrl
        serverUrl = ui.getResponse('URL to use to contact rBuilder'
                                       ' (start with http:// or https://)',
                                       validationFn=validateUrl,
                                       default=defaultUrl)
        ui.write('rBuilder contacted successfully.')

        if serverUrl.endswith('/'):
            serverUrl = serverUrl[:-1]

        return serverUrl

    def getRmakeUrl(self, serverUrl, rmakeUrl=None):
        ui = self.handle.ui
        useRbaRmake = False
        if not serverUrl.endswith('rpath.org'):
            if self.handle.facade.rbuilder.checkForRmake(serverUrl):
                useRbaRmake = ui.getYn("Do you want to use the rMake server "
                    "running on the rBuilder Appliance?  'N' will use the "
                    "rMake server on this local machine. (Y/N):",
                    default=True)
        if useRbaRmake:
            rmakeUrl = '%s:%s' %(
                serverUrl.replace('http:', 'https:'),
                str(constants.RMAKE_PORT))
        return rmakeUrl

    def getUserPass(self, defaultUser, defaultPassword):
        ui = self.handle.ui
        user =  ui.getResponse('Your rbuilder user name',
                               default=defaultUser)
        passwd = ui.getPassword('Your rbuilder password',
                                default=defaultPassword,
                                verify=True)
        return user, passwd

    def promptReEnterUrl(self):
        ui = self.handle.ui
        reEnterUrl = ui.getYn(
            'Would you like to re-enter the rBuilder url? (Y/N)',
            default=False)
        return reEnterUrl

    def promptReEnterUserPasswd(self):
        ui = self.handle.ui
        reEnterUserPasswd = ui.getYn(
            'Would you like to re-enter the user name and '
            'password? (Y/N)', default=False)
        return reEnterUserPasswd

    @_requiresHome
    def updateConfig(self, cfg=None):
        ui = self.handle.ui
        facade = self.handle.facade

        if cfg is None:
            cfg = self.handle.getConfig()

        rBuilderAuth = facade.rbuilder._getBaseServerUrlData()
        rBuilderServerUrl, rBuilderUser, rBuilderPassword = rBuilderAuth

        rMakeCfg = facade.rmake._getBaseRmakeConfig()

        conaryCfg = facade.conary._getBaseConaryConfig()

        if cfg.serverUrl is None:
            cfg.serverUrl = rBuilderServerUrl

        if cfg.name:
            defaultName = cfg.name
        else:
            defaultName = conaryCfg.name

        if cfg.contact:
            defaultContact = cfg.contact
        else:
            defaultContact = conaryCfg.contact

        if cfg.user:
            defaultUser = cfg.user[0]
            defaultPassword = cfg.user[1]
        else:
            defaultUser = rBuilderUser
            defaultPassword = rBuilderPassword

        if cfg.rmakeUrl:
            rmakeUrl = cfg.rmakeUrl
        else:
            rmakeUrl = rMakeCfg.rmakeUrl

        authorized = False
        reEnterUrl = True
        reEnterUserPasswd = True

        while not authorized:
            if reEnterUrl:
                serverUrl = self.getServerUrl(cfg.serverUrl)
            validRbuilderUrl = self.handle.facade.rbuilder.validateRbuilderUrl(
                serverUrl)
            if not validRbuilderUrl[0]:
                ui.write('The rBuilder url is a valid server, but there was '
                    'an error communicating with the rBuilder at that '
                    'location: %s' % validRbuilderUrl[1])
                reEnterUrl = self.promptReEnterUrl()
                if reEnterUrl:
                    continue

            if reEnterUserPasswd:
                user, passwd = self.getUserPass(defaultUser, defaultPassword)
            validCredentials = self.handle.facade.rbuilder.validateCredentials(
                user, passwd, serverUrl)
            authorized = validCredentials

            if not authorized:
                ui.write('The specified credentials were not successfully '
                         'authorized against the rBuilder at %s.' % serverUrl)
                reEnterUrl = self.promptReEnterUrl()

                if reEnterUrl:
                    reEnterUserPasswd = False
                else:
                    reEnterUserPasswd = self.promptReEnterUserPasswd()
                if not reEnterUrl and not reEnterUserPasswd:
                    # continue anyway
                    authorized = True
            else:
                ui.write('rBuilder authorized successfully.')

        rmakeUrl = self.getRmakeUrl(serverUrl, rmakeUrl)
        if rmakeUrl:
            cfg.rmakeUrl = rmakeUrl

        keepPass = ui.getYn("Store your password in the local "
                "configuration file?", default=False)
        if keepPass:
            cfg.user = (user, passwd)
        else:
            cfg.user = (user, None)

        cfg.serverUrl = serverUrl
        cfg.name = ui.getResponse('Name to display when committing',
                                  default=defaultName)
        cfg.contact = ui.getResponse('Contact - usually email or url',
                                     default=defaultContact)

        homeRbuildRc = os.sep.join((os.environ['HOME'], '.rbuildrc'))
        self._writeConfiguration(homeRbuildRc, cfg=cfg,
            header='# This file will be overwritten by the'
                   ' "rbuild config --ask" command',
            replaceExisting=True)

        # Only write rmakeUser to rbuildrc if it existed before, don't copy if
        # it isn't set. This ensures that it inherits from 'user' and thus the
        # password prompt only happens once. However, do always write rmakeUser
        # to .rmakerc-rbuild
        copyRmake = False
        if not cfg.rmakeUser:
            cfg.rmakeUser = cfg.user
            copyRmake = True
        self.writeConaryConfiguration()
        self.writeRmakeConfiguration()
        # For operations after the initial setup
        cfg.user = (user, passwd)
        if copyRmake:
            cfg.rmakeUser = cfg.user

#{ Synchronizing Conary and rMake configuration
    @_requiresHome
    def writeConaryConfiguration(self):
        '''
        Write a ~/.conaryrc-rbuild file, and possibly a ~/.conaryrc
        referencing it, based on the contents of the rMakeCfg.
        '''
        #
        homeConaryConfig = os.sep.join((os.environ['HOME'], '.conaryrc'))
        cfg = self.handle.getConfig()
        cf = self.handle.facade.conary

        conaryCfg = cf.getConaryConfig(useCache=False)
        conaryCfg.name = cfg.name
        conaryCfg.contact = cfg.contact
        keys = set(['contact', 'name', 'user', 'repositoryMap'])
        if cfg.externalPassword:
            # This will replace the existing glob for * ONLY containing passwd
            conaryCfg.user.addServerGlob('*', cfg.user[0], '')
        self._writeConfiguration(homeConaryConfig + '-rbuild', cfg=conaryCfg,
            header='\n'.join((
            '# This file will be overwritten automatically by rBuild',
            '# You can ignore it by removing the associated includeConfigFile',
            '# line from ~/.conaryrc')),
            keys=keys,
            replaceExisting=True)

        self._writeConfiguration(homeConaryConfig, cfg=None,
            header='\n'.join((
                '# Include config file maintained by rBuild:',
                'includeConfigFile ~/.conaryrc-rbuild')),
            replaceExisting=False)


    @_requiresHome
    def writeRmakeConfiguration(self):
        '''
        Write a ~/.rmakerc-rbuild file, and possibly a ~/.rmakerc
        referencing it, based on the contents of the rMakeCfg.
        '''
        homeRmakeConfig = os.sep.join((os.environ['HOME'], '.rmakerc'))
        cfg = self.handle.getConfig()
        rf = self.handle.facade.rmake
        rmakeCfg = rf._getRmakeConfig(includeContext=False)
        keys = set(['rmakeUser', 'rmakeUrl', 'rbuilderUrl'])
        if cfg.externalPassword:
            rmakeCfg.rmakeUser = (cfg.user[0], '')
        self._writeConfiguration(homeRmakeConfig + '-rbuild', cfg=rmakeCfg,
            header='\n'.join((
            '# This file will be overwritten automatically by rBuild.',
            '# You can ignore it by removing the associated includeConfigFile',
            '# line from ~/.rmakerc')),
            keys=keys,
            replaceExisting=True)

        self._writeConfiguration(homeRmakeConfig, cfg=None,
            header='\n'.join((
                '# Include config file maintained by rBuild:',
                'includeConfigFile ~/.rmakerc-rbuild')),
            replaceExisting=False)

    @staticmethod
    def _writeConfiguration(pathName, cfg=None, header=None, keys=None,
                            replaceExisting=False):
        '''
        Write a configuration file C{pathName}, optionally replacing an
        existing configuration files, with C{contents} as provided.
        @param pathName: Path to file to replace
        @type pathName: string
        @param cfg: Conary-style cfg object to write to C{pathName}
        @type cfg: conary.lib.cfg._Config or None
        @param header: Optional text to prepend to the file
        @type header: string
        @param keys: If not None (default), comprehensive list of keys to write
        @type keys: iterable of strings
        @param replaceExisting: Replace any existing C{pathName} (False)
        @type replaceExisting: bool
        '''
        if not replaceExisting and os.path.exists(pathName):
            return
        # passwords may go in config files
        oldUmask = os.umask(077)
        try:
            f = file(pathName, 'w')
            if header is not None:
                f.write(header)
                if not header.endswith('\n'):
                    f.write('\n')
            if cfg is not None:
                if keys is not None:
                    # conary.lib.cfg._Config does not expose an interface
                    # for limiting the keys written when writing a config
                    options = {'prettyPrint': 'False'}
                    for name, item in sorted(cfg._options.iteritems()):
                        if name in keys:
                            item.writeDoc(f, options)
                            cfg._writeKey(f, item, cfg[name], options)
                else:
                    cfg.store(f)
            f.close()
        finally:
            os.umask(oldUmask)
#}
