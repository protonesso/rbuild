#!/usr/bin/python
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


'''
unit tests for rmake facade
'''

import os
import robj
import socket
import time
import urllib2
from collections import namedtuple
from rpath_proddef import api1 as proddef
from StringIO import StringIO

from rbuild import errors
from rbuild import facade as fac_mod
from rbuild.facade import rbuilderfacade
from rbuild_test import rbuildhelp
from testutils import mock
from xobj import xobj


TARGET_XML = '''\
<?xml version='1.0' encoding='UTF-8'?>
<target>
    <description>Foo</description>
    <name>foo</name>
    <target_type_name>vmware</target_type_name>
    <zone_name>local</zone_name>
</target>
'''


class RbuilderConfigTest(rbuildhelp.RbuildHelper):
    def test_rBuilderConfig(self):
        oldHome = os.environ['HOME']
        try:
            os.environ['HOME'] = self.workDir
            rbcfg = rbuilderfacade._rBuilderConfig()
            self.assertEquals(rbcfg.serverUrl, None)
            serverUrl = 'https://user:password@host/path'
            file(self.workDir + '/.rbuilderrc', 'w+').write(
                'serverUrl %s\n' %serverUrl)
            rbcfg = rbuilderfacade._rBuilderConfig()
            self.assertEquals(rbcfg.serverUrl, serverUrl)
        finally:
            os.environ['HOME'] = oldHome


class RbuilderFacadeTest(rbuildhelp.RbuildHelper):
    def prep(self):
        handle = mock.MockObject()
        cfg = mock.MockObject(serverUrl = 'http://localhost',
                              user=('foo', 'bar'))
        handle.getConfig._mock.setReturn(cfg)
        handle.productStore.getActiveStageName._mock.setReturn('devel')
        facade = rbuilderfacade.RbuilderFacade(handle)

        return handle, facade

    def test_getRbuilderClient(self):
        _, facade = self.prep()
        mockClass = mock.MockObject()
        facade._getRbuilderClient(mockClass)
        mockClass._mock.assertCalled('http://localhost', 'foo', 'bar',
                                     facade._handle)

    def test_getRbuilderClientDefault(self):
        _, facade = self.prep()
        mock.mock(rbuilderfacade, 'RbuilderRPCClient')
        facade._getRbuilderClient()
        rbuilderfacade.RbuilderRPCClient._mock.assertCalled('http://localhost',
                                                         'foo', 'bar',
                                                         facade._handle)

    def test_getRbuilderRPCClient(self):
        _, facade = self.prep()
        mock.mock(rbuilderfacade, 'RbuilderRPCClient')
        facade._getRbuilderRPCClient()
        rbuilderfacade.RbuilderRPCClient._mock.assertCalled('http://localhost',
                                                         'foo', 'bar',
                                                         facade._handle)

    def test_getRbuilderRESTClient(self):
        _, facade = self.prep()
        mock.mock(rbuilderfacade, 'RbuilderRESTClient')
        facade._getRbuilderRESTClient()
        rbuilderfacade.RbuilderRESTClient._mock.assertCalled(
            'http://localhost', 'foo', 'bar', facade._handle)

    def test_getBaseServerUrl(self):
        _, facade = self.prep()
        rbcfg = mock.MockObject()
        rbcfg._mock.enable('serverUrl')
        rbcfg.serverUrl = None
        def _rBuilderConfig():
            return rbcfg
        self.mock(rbuilderfacade, '_rBuilderConfig', _rBuilderConfig)
        self.assertEquals(facade._getBaseServerUrl(), None)
        serverUrl = 'https://user:password@host/path'
        rbcfg.serverUrl = serverUrl
        self.assertEquals(facade._getBaseServerUrl(), serverUrl)

    def test_getBaseServerUrlData(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getBaseServerUrl)
        facade._getBaseServerUrl._mock.setDefaultReturn(None)
        self.assertEquals(facade._getBaseServerUrlData(),
                          (None, None, None))
        serverUrl = 'https://user:password@host/path'
        facade._getBaseServerUrl._mock.setDefaultReturn(serverUrl)
        self.assertEquals(facade._getBaseServerUrlData(),
                          ('https://host/path', 'user', 'password'))
        serverUrl = 'https://user@host/path'
        facade._getBaseServerUrl._mock.setDefaultReturn(serverUrl)
        self.assertEquals(facade._getBaseServerUrlData(),
                          ('https://host/path', 'user', None))
        serverUrl = 'https://host/path'
        facade._getBaseServerUrl._mock.setDefaultReturn(serverUrl)
        self.assertEquals(facade._getBaseServerUrlData(),
                          ('https://host/path', None, None))

    def testBuildAllImagesForStage(self):
        handle, facade = self.prep()
        handle.product.getProductShortname._mock.setReturn('shortname')
        handle.product.getProductVersion._mock.setReturn('1.0')
        mock.mockMethod(facade._getRbuilderRPCClient)
        client = facade._getRbuilderRPCClient()
        client.startProductBuilds._mock.setReturn([1], 'shortname', '1.0',
                'devel', buildNames=None, groupSpecs=None, groupVersion=None)
        buildIds = facade.buildAllImagesForStage()
        self.assertEquals(buildIds, [1])


    def testBuildAllImagesForStage_groupSpecs(self):
        handle, facade = self.prep()
        handle.product.getProductShortname._mock.setReturn('shortname')
        handle.product.getProductVersion._mock.setReturn('1.0')
        client = facade._getRbuilderRPCClient()
        mock.mockMethod(facade._getRbuilderRPCClient, returnValue=client)
        # Make sure we don't pass in groupSpecs if not necessary
        mock.mock(client, 'server')
        client.server.getProductVersionListForProduct._mock.setDefaultReturn(
                (False, [(1, 1, 'sas', '1.0', '')]))
        client.server.getProjectIdByHostname._mock.setDefaultReturn(
                (False, 1))

        client.server.newBuildsFromProductDefinition._mock.setDefaultReturn(
                (False, [1]))
        buildIds = facade.buildAllImagesForStage()
        self.assertEquals(buildIds, [1])
        _mock = client.server.newBuildsFromProductDefinition._mock
        self.assertEquals(_mock.calls, [((1, 'devel', False, None), ())])
        _mock.popCall()

        # Now invoke with groupSpecs
        groupSpecs = [ 'group-1=cny.org@ex:1', 'group-2=cny.org@ex:2' ]
        buildIds = facade.buildAllImagesForStage(groupSpecs=groupSpecs)
        self.assertEquals(_mock.calls, [((1, 'devel', False, None, None, groupSpecs), ())])

    def testBuildAllImagesForStage_groupVersion(self):
        handle, facade = self.prep()
        handle.productStore.getActiveStageName._mock.setReturn("devel")
        handle.product.getProductShortname._mock.setReturn('shortname')
        handle.product.getProductVersion._mock.setReturn('1.0')
        handle.product.getLabelForStage._mock.setReturn(
            'shortname@rpath:shortname-1.0-devel', 'devel')

        mock.mockMethod(facade._getRbuilderRPCClient)
        mock.mockMethod(facade.getGroups)
        facade.getGroups._mock.appendReturn(
            [mock.MockObject(trailingVersion="1.0-1-1")], "shortname",
            "shortname@rpath:shortname-1.0-devel")

        client = facade._getRbuilderRPCClient()

        _mock = client.startProductBuilds._mock

        # Make sure we don't pass in groupVersion if not necessary
        _mock.setReturn([1], 'shortname', '1.0', 'devel', buildNames=None,
                groupSpecs=None, groupVersion=None)

        buildIds = facade.buildAllImagesForStage()
        self.assertEquals(buildIds, [1])

        self.assertEquals(_mock.calls, [(('shortname', '1.0', 'devel'),
                (('buildNames', None), ('groupSpecs', None),
                 ('groupVersion', None)))])
        _mock.popCall()
        handle.product.getLabelForStage._mock.assertNotCalled()

        # Now invoke with groupVersion
        _mock.setReturn([2], 'shortname', '1.0', 'devel',
                buildNames=None, groupSpecs=None,
                groupVersion="shortname@rpath:shortname-1.0-devel/1.0-1-1")
        buildIds = facade.buildAllImagesForStage(groupVersion="1.0-1-1")
        self.assertEquals(buildIds, [2])
        self.assertEquals(_mock.calls, [(('shortname', '1.0', 'devel'),
              (('buildNames', None), ('groupSpecs', None),
               ('groupVersion', "shortname@rpath:shortname-1.0-devel/1.0-1-1")))])
        handle.product.getLabelForStage._mock.assertCalled('devel')

        # now invoke with bad groupVersion
        self.assertRaises(errors.BadParameterError, facade.buildAllImagesForStage,
                          groupVersion="bad-version")

    def testWatchImages(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRPCClient)
        facade.watchImages([1])
        facade._getRbuilderRPCClient().watchImages._mock.assertCalled([1], interval=5, quiet=False, timeout=0)

    def testGetBuildFiles(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRPCClient)
        facade.getBuildFiles(1)
        facade._getRbuilderRPCClient().getBuildFiles._mock.assertCalled(1)

    def testGetProductLabelFromNameAndVersion(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRPCClient)
        facade.getProductLabelFromNameAndVersion('foo', '1')
        facade._getRbuilderRPCClient().getProductLabelFromNameAndVersion._mock.assertCalled('foo', '1')

    def testCheckForRmake(self):
        _, facade = self.prep()
        mock.mock(socket, 'socket')
        ret = facade.checkForRmake('http://localhost')
        socket.socket().connect._mock.assertCalled(('localhost', 9999))
        socket.socket().close._mock.assertCalled()
        self.assertEquals(ret, True)
        ret = facade.checkForRmake('localhost')
        self.assertEquals(ret, False)
        socket.socket().connect._mock.raiseErrorOnAccess(socket.error)
        ret = facade.checkForRmake('http://localhost')
        self.assertEquals(ret, False)

    def testValidateUrl(self):
        mock.mock(urllib2, 'urlopen')
        connection = mock.MockObject()
        urllib2.urlopen._mock.setReturn(connection, 'http://foo/conaryrc')
        connection.read._mock.setReturn('data', 1024)
        handle, facade = self.prep()
        assert(facade.validateUrl('http://foo') is True)
        connection.read._mock.assertCalled(1024)
        err = RuntimeError('foo')
        connection.read._mock.raiseErrorOnAccess(err)
        assert(facade.validateUrl('http://foo') is False)
        handle.ui.writeError._mock.assertCalled("Error contacting '%s': %s", 'http://foo', err)

    def testValidateRbuilderUrl(self):
        handle, facade = self.prep()
        mock.mock(rbuilderfacade, 'RbuilderRPCClient')
        rbuilderfacade.RbuilderRPCClient().checkAuth._mock.setDefaultReturn(dict(authorized=True))
        rbuilderfacade.RbuilderRPCClient._mock.popCall()
        ret = facade.validateRbuilderUrl('http://foo')
        self.assertEquals(rbuilderfacade.RbuilderRPCClient._mock.popCall(),
                          (('http://foo', '', '', handle), ()))
        assert((True, '')==ret)
        e = Exception()
        rbuilderfacade.RbuilderRPCClient().checkAuth._mock.raiseErrorOnAccess(e)
        ret = facade.validateRbuilderUrl('http://foo')
        assert((False, e)==ret)

    def testValidateCredentials(self):
        handle, facade = self.prep()
        mock.mock(rbuilderfacade, 'RbuilderRPCClient')
        rbuilderfacade.RbuilderRPCClient().checkAuth._mock.setDefaultReturn(dict(authorized=True))
        rbuilderfacade.RbuilderRPCClient._mock.popCall()
        auth = facade.validateCredentials('user', 'pass', 'http://foo')
        assert(auth is True)
        self.assertEquals(rbuilderfacade.RbuilderRPCClient._mock.popCall(),
                          (('http://foo', 'user', 'pass', handle), ()))
        rbuilderfacade.RbuilderRPCClient().checkAuth._mock.setDefaultReturn(dict())
        auth = facade.validateCredentials('user', 'pass', 'http://foo')
        assert(auth is False)

    def testGetProjectUrl(self):
        handle, facade = self.prep()
        mock.mockMethod(facade._getBaseServerUrlData)._mock.setDefaultReturn(('asdf', None, None))
        handle.product.getProductShortname._mock.setDefaultReturn('pdct')
        self.assertEquals(facade.getBuildUrl(5), 'asdf/project/pdct/build?id=5')

    def testGetProductDefinitionSchemaVersion(self):
        handle, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRESTClient)
        facade.getProductDefinitionSchemaVersion()
        facade._getRbuilderRESTClient().getProductDefinitionSchemaVersion._mock.assertCalled()

    def testCreateProject(self):
        handle, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRESTClient)
        handle.facade.conary.isValidLabel._mock.appendReturn(True, "label")
        handle.facade.conary.isValidLabel._mock.appendReturn(False, "invalid.label")
        mock.mock(facade, 'isValidUrl')
        facade.isValidUrl._mock.appendReturn(True)
        facade.isValidUrl._mock.appendReturn(False, "illegal.url")
        facade.isValidUrl._mock.appendReturn(False, None)
        # test valid non-external project
        facade.createProject('title', 'shortname', 'hostname', 'domain.name')
        # test valid external project, no upstream url
        facade.createProject('title', 'shortname', 'hostname', 'domain.name',
                             external=True, external_params=(["label"], None))
        # test valid external project, upstream url
        facade.createProject('title', 'shortname', 'hostname', 'domain.name',
                             external=True, external_params=(["label"], "url"))
        # test invalid shortname
        self.assertRaises(errors.BadParameterError, facade.createProject,
                'title', 'illegal.short')
        # test invalid hostname
        self.assertRaises(errors.BadParameterError, facade.createProject,
                'title', 'short', 'illegal.host')
        # test invalid domain name
        self.assertRaises(errors.BadParameterError, facade.createProject,
                'title', 'short', None, 'bad.0.domain')
        # test invalid upstream label
        self.assertRaises(errors.BadParameterError, facade.createProject,
                'title', 'short', 'hostname', 'hostname.domain', external=True,
                external_params=(['invalid.label'], None))
        self.assertRaises(errors.BadParameterError, facade.createProject,
                'title', 'short', 'hostname', 'hostname.domain', external=True,
                external_params=(['label'], "illegal.url"))

    def testCreateBranch(self):
        handle, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRESTClient)
        facade.createBranch('proj', 'branch', 'plat')
        facade._getRbuilderRESTClient().createBranch._mock.assertCalled(
                'proj', 'branch', 'plat', None, '')
        self.assertRaises(errors.BadParameterError, facade.createBranch,
                'proj', '-1', 'plat')

    def testCreateExistingBranch(self):
        handle, facade = self.prep()
        cli = rbuilderfacade.RbuilderRESTClient('/foo', 'username',
                'password', handle)
        mock.mockMethod(facade._getRbuilderRESTClient, returnValue=cli)
        projectBranches = mock.MockObject()
        project = mock.MockObject(project_branches=projectBranches)
        mock.mockMethod(cli.getProject, returnValue=project)

        invocations = []
        def append(projectBranch):
            invocations.append(projectBranch)
            raise robj.errors.HTTPConflictError(uri='/fake',
                    status='Conflict', reason='Just because', response="")
        projectBranches._mock.set(append=append)
        e = self.assertRaises(errors.RbuildError, facade.createBranch,
                'proj', 'branch', 'plat')
        self.assertEquals(str(e), "Branch named 'branch' already exists")

    def testGetProject(self):
        handle, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRESTClient)
        facade._getRbuilderRESTClient().getProject._mock.setReturn('project', 'shortname')
        self.assertEqual(facade.getProject('shortname'), 'project')

    def testListPlatforms(self):
        handle, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRESTClient)
        facade._getRbuilderRESTClient().listPlatforms._mock.setReturn(['platform'])
        self.assertEqual(facade.listPlatforms(), ['platform'])

    def testGetWindowsBuildService(self):
        handle, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRESTClient)
        facade._getRbuilderRESTClient().getWindowsBuildService._mock.setReturn('rwbs')
        self.assertEqual(facade.getWindowsBuildService(), 'rwbs')

    def testGetEnabledTargets(self):
        handle, facade = self.prep()
        _target1 = mock.MockObject()
        _target1._mock.set(is_configured=u'true')
        _target1._mock.set(credentials_valid=u'true')

        _target2 = mock.MockObject()
        _target2._mock.set(is_configured=u'true')
        _target2._mock.set(credentials_valid=u'false')

        _target3 = mock.MockObject()
        _target3._mock.set(is_configured=u'false')
        _target3._mock.set(credentials_valid=u'true')

        _target4 = mock.MockObject()
        _target4._mock.set(is_configured=u'false')
        _target4._mock.set(credentials_valid=u'false')

        mock.mock(
            facade, 'getTargets', [_target1, _target2, _target3, _target4])
        rv = facade.getEnabledTargets()
        self.assertEqual(rv, [_target1])

    def testGetTarget(self):
        handle, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRESTClient)
        facade._getRbuilderRESTClient().getTarget._mock.setReturn(
            'target', 'foo')
        self.assertEqual(facade.getTarget('foo'), 'target')

    def testGetTargets(self):
        handle, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRESTClient)
        facade._getRbuilderRESTClient().getTargets._mock.setReturn(
            ['foo', 'bar'])
        self.assertEqual(facade.getTargets(), ['foo', 'bar'])

    def testGetPlatform(self):
        handle, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRESTClient)
        _platform1 = mock.MockObject()
        _platform1._mock.set(label='label1')
        _platform2 = mock.MockObject()
        _platform2._mock.set(label='label2')
        facade._getRbuilderRESTClient().api._mock.set(
            platforms=[_platform1, _platform2])
        self.assertEqual(facade.getPlatform('label2'), _platform2)
        self.assertEqual(facade.getPlatform('no label'), None)

    def testGetProjectBranches(self):
        handle, facade = self.prep()
        mock.mockMethod(facade.getProject)

        _branch1 = mock.MockObject()
        _branch1._mock.set(name='1')
        _branch1._mock.set(label='foo.com@foo:foo-1')
        _branch1._mock.enable('non_field')

        _branch2 = mock.MockObject()
        _branch2._mock.set(name='2')
        _branch2._mock.set(label='foo.com@bar:foo-2')
        _branch2._mock.enable('non_field')

        _project = mock.MockObject()
        _project._mock.set(name='foo')
        _project._mock.set(domain_name='com')
        _project._mock.set(project_branches=[_branch1, _branch2])

        facade.getProject._mock.setReturn(_project, 'foo')
        facade.getProject._mock.setReturn(_project, 'foo.com')

        err = self.assertRaises(
            TypeError,
            facade.getProjectBranches
            )
        self.assertIn('Required argument', str(err))

        # get branches by project short name
        rv = facade.getProjectBranches('foo')
        self.assertEqual(rv, [_branch1, _branch2])

        # get branches by project hostname
        rv = facade.getProjectBranches('foo.com')
        self.assertEqual(rv, [_branch1, _branch2])

        # order by name, descending
        rv = facade.getProjectBranches('foo', order_by='-name')
        self.assertEqual(rv, [_branch2, _branch1])

        # explicitly order by label ascending
        rv = facade.getProjectBranches('foo', order_by='+label')
        self.assertEqual(rv, [_branch2, _branch1])

        # implicitly order by label ascending
        rv = facade.getProjectBranches('foo', order_by='label')
        self.assertEqual(rv, [_branch2, _branch1])

        # ordering by a field that doesn't exist
        self.assertRaises(
            AttributeError,
            facade.getProjectBranches,
            'foo',
            order_by='non_field',
            )
        self.assertRaises(
            AttributeError,
            facade.getProjectBranches,
            'foo',
            order_by='+non_field',
            )
        self.assertRaises(
            AttributeError,
            facade.getProjectBranches,
            'foo',
            order_by='-non_field',
            )

    def testIsValidBranchName(self):
        handle, facade = self.prep()

        # value is None
        self.assertFalse(facade.isValidBranchName(None))

        # empty string
        self.assertFalse(facade.isValidBranchName(''))

        # value begins with non-alphanumeric
        self.assertFalse(facade.isValidBranchName('.a'))

        # value contians invalid characters
        self.assertFalse(facade.isValidBranchName('a_b'))
        self.assertFalse(facade.isValidBranchName('a-b'))
        self.assertFalse(facade.isValidBranchName('a%%b'))
        self.assertFalse(facade.isValidBranchName('a!b'))

    def testIsValidDomainName(self):
        handle, facade = self.prep()

        # value is None
        self.assertTrue(facade.isValidDomainName(None))

        # empty string
        self.assertTrue(facade.isValidDomainName(''))

        # value begins with non-alphabetic
        self.assertFalse(facade.isValidDomainName('9a'))
        self.assertFalse(facade.isValidDomainName('-a'))

        # value contians invalid characters
        self.assertFalse(facade.isValidDomainName('a_b'))
        self.assertFalse(facade.isValidDomainName('a%%b'))
        self.assertFalse(facade.isValidDomainName('a!b'))

    def testIsValidShortName(self):
        handle, facade = self.prep()

        # short name is None
        self.assertFalse(facade.isValidShortName(None))

        # shotname is empty string
        self.assertFalse(facade.isValidShortName(''))

        # short name is too long
        self.assertFalse(facade.isValidShortName('a' * 63))
        self.assertFalse(facade.isValidShortName('a' * 163))

        # shortname begins with non-alphabetic
        self.assertFalse(facade.isValidShortName('9a'))
        self.assertFalse(facade.isValidShortName('-a'))

        # some invalid characters
        self.assertFalse(facade.isValidShortName('a_b'))
        self.assertFalse(facade.isValidShortName('a.b'))
        self.assertFalse(facade.isValidShortName('a%%b'))
        self.assertFalse(facade.isValidShortName('a!b'))

    def testIsValidUrl(self):
        mock.mock(urllib2, 'urlopen')
        connection = mock.MockObject()
        urllib2.urlopen._mock.setReturn(connection, 'http://foo')
        connection.read._mock.setReturn('data', 1024)
        handle, facade = self.prep()
        assert(facade.isValidUrl('http://foo') is True)

        # False on generic exception
        connection.read._mock.assertCalled(1024)
        err = RuntimeError('foo')
        connection.read._mock.raiseErrorOnAccess(err)
        assert(facade.isValidUrl('http://foo') is False)

        # True on unauthorized
        err = urllib2.HTTPError("http://foo", 401, "Unauthorized", "", StringIO())
        connection.read._mock.raiseErrorOnAccess(err)
        assert(facade.isValidUrl('http://foo') is True)

        # False on non 401
        err = urllib2.HTTPError("http://foo", 404, "Not Found", "", StringIO())
        connection.read._mock.raiseErrorOnAccess(err)
        assert(facade.isValidUrl('http://foo') is False)

    def testIsAdmin(self):
        handle, facade = self.prep()

        _user_bar = mock.MockObject()
        _user_bar._mock.set(is_admin='true')

        _user_foo = mock.MockObject()
        _user_foo._mock.set(is_admin='false')

        _client = mock.MockObject()
        _client.getUsers._mock.setReturn([_user_bar], user_name='bar')
        _client.getUsers._mock.setReturn([_user_foo], user_name='foo')
        mock.mockMethod(facade._getRbuilderRESTClient, _client)

        # don't pass userName
        self.assertFalse(facade.isAdmin())

        # with username
        self.assertTrue(facade.isAdmin(userName='bar'))
        self.assertFalse(facade.isAdmin(userName='foo'))


class RbuilderRPCClientTest(rbuildhelp.RbuildHelper):
    def _getClient(self):
        mock.mock(fac_mod, 'ServerProxy')
        return rbuilderfacade.RbuilderRPCClient('http://localhost', 'foo', 'bar',
            mock.MockObject())

    def testRbuilderRPCClientInit(self):
        mock.mock(fac_mod, 'ServerProxy')
        rbuilderfacade.RbuilderRPCClient('http://localhost', 'foo', 'bar', None)
        fac_mod.ServerProxy._mock.assertCalled(
                'http://localhost/xmlrpc-private',
                username='foo', password='bar', allow_none=True)
        rbuilderfacade.RbuilderRPCClient('https://localhost2', 'foo2', 'bar', None)
        fac_mod.ServerProxy._mock.assertCalled(
                'https://localhost2/xmlrpc-private',
                username='foo2', password='bar', allow_none=True)

    def testGetBranchIdFromName(self):
        client = self._getClient()
        server = client.server
        server.getProjectIdByHostname._mock.setReturn((False, 32),
                                                       'foo.rpath.org')
        productVersionList = [(1, 32, 'rpl', '1.0', 'version 1.0'),
                              (2, 32, 'rpl', '2.0', 'version 2.0')]
        returnValue = (False, productVersionList)
        server.getProductVersionListForProduct._mock.setReturn(returnValue, 32)
        rc = client.getBranchIdFromName('foo.rpath.org', '1.0')
        self.assertEqual(rc, 1)

        err = self.assertRaises(errors.RbuildError,
                    client.getBranchIdFromName,
                    'foo.rpath.org', '3.0')
        self.assertEquals(str(err), '3.0 is not a valid version for product '
            'foo.rpath.org.\nValid versions are: 1.0, 2.0')

        server.getProductVersionListForProduct._mock.setReturn((False, []), 32)
        err = self.assertRaises(errors.RbuildError,
                    client.getBranchIdFromName,
                    'foo.rpath.org', '3.0')
        self.assertEquals(str(err), '3.0 is not a valid version for product '
            'foo.rpath.org.\nNo versions found for product foo.rpath.org.')
        server.getProductVersionListForProduct._mock.setReturn(returnValue, 32)

        server.getProductVersionListForProduct._mock.setReturn(
                (True, ('BarError', '')), 32)
        assertRaiseArgs = (errors.RbuildError,
            client.getProductLabelFromNameAndVersion, 'foo.rpath.org', '1.0')
        err = self.assertRaises(*assertRaiseArgs)
        self.assertEqual(str(err), "rBuilder error BarError: ''")

        server.getProjectIdByHostname._mock.setReturn(
                (True, ('BazError', 1337)), 'foo.rpath.org')
        err = self.assertRaises(*assertRaiseArgs)
        self.assertEqual(str(err), "rBuilder error BazError: 1337")

    def testGetProductLabelFromNameAndVersion2(self):
        client = self._getClient()
        server = client.server
        mock.mockMethod(client.getBranchIdFromName)
        client.getBranchIdFromName._mock.setReturn(1, 'foo.rpath.org', '1.0')
        client.getBranchIdFromName._mock.setReturn(2, 'foo.rpath.org', '2.0')
        server.getProductDefinitionForVersion._mock.setReturn(
                                                    (False, 'stream'), 1)
        mock.mock(proddef, 'ProductDefinition')
        product = mock.MockObject()
        proddef.ProductDefinition._mock.setReturn(product, 'stream')
        product.getProductDefinitionLabel._mock.setReturn(
                                                        'foo.rpath.org@rpl:1')
        rc = client.getProductLabelFromNameAndVersion('foo.rpath.org', '1.0')
        assert(rc == 'foo.rpath.org@rpl:1')

        server.getProductDefinitionForVersion._mock.setReturn(
                (True, ('FooError', '')), 1)
        err = self.assertRaises(errors.RbuildError,
                client.getProductLabelFromNameAndVersion,
                'foo.rpath.org', '1.0')
        self.assertEqual(str(err), "rBuilder error FooError: ''")

    def testStartProductBuilds(self):
        client = self._getClient()
        server = client.server
        mock.mockMethod(client.getBranchIdFromName)
        client.getBranchIdFromName._mock.setReturn(2, 'foo.rpath.org', '2.0')

        server.newBuildsFromProductDefinition._mock.setReturn(
                [False, [1, 2, 3, 4, 5]],
                2, 'devel', False, None)
        buildIds = client.startProductBuilds('foo.rpath.org', '2.0', 'devel')
        assert(buildIds == [1, 2, 3, 4, 5])

        server.newBuildsFromProductDefinition._mock.setReturn(
                [False, [6]],
                2, 'devel', False, None, '1.0-1-1')
        buildIds = client.startProductBuilds('foo.rpath.org', '2.0', 'devel',
                                             groupVersion='1.0-1-1')
        assert(buildIds == [6])

        # now test for error conditions
        server.newBuildsFromProductDefinition._mock.setReturn(
                [True, ['ErrorClass', 'message']],
                2, 'devel', False, None)
        err = self.assertRaises(errors.RbuildError,
                                client.startProductBuilds,
                                'foo.rpath.org', '2.0', 'devel')
        self.failUnlessEqual(str(err), "rBuilder error ErrorClass: 'message'")

        server.newBuildsFromProductDefinition._mock.setReturn((True,
            ['TroveNotFoundForBuildDefinition', [[
            "Trove 'group-dumponme-appliance' has no matching flavors "
            "for '~X,~!alternatives,!bootstrap,!cross,~!dom0,!domU,~vmware"
            ",~!xen,~!xfce is: x86(~cmov,~i486,~i586,~i686,~mmx,~sse,~sse2)'"]]]),
                                    2, 'devel', False)
        err = self.assertRaises(errors.RbuildError,
                                client.startProductBuilds,
                                'foo.rpath.org', '2.0', 'devel')

    def testWatchImages(self):
        client = self._getClient()
        server = client.server
        mock.mock(time, 'sleep')
        server.getBuildStatus._mock.setReturns(
                            [(False, {'message' : 'foo', 'status' : 0}),
                             (False, {'message' : 'bar', 'status' : 300})],
                                        1)
        server.getBuildStatus._mock.setReturns(
                            [(False, {'message' : 'bam', 'status' : 200}),
                             (False, {'message' : 'zap', 'status' : 500})],
                                        2)
        client.watchImages([1, 2])
        client._handle.ui.info._mock.assertNotCalled()
        client._handle.ui.warning._mock.assertNotCalled()
        client._handle.ui.error._mock.assertNotCalled()
        self.assertEquals(
            [x[0][0]%x[0][1:] for x in client._handle.ui.write._mock.calls],
            ['1: Waiting "foo"',
             '2: Built "bam"',
             '1: Finished "bar"',
             '2: Unknown "zap"',
             'All jobs completed',
             'Finished builds:',
             "    Build 1 ended with 'Finished' status: bar",
             "    Build 2 ended with 'Unknown' status: zap"])

        server.getBuildStatus._mock.setReturns(
                            [(False, {'message' : 'bam', 'status' : 200}),
                             (True, ('Error', ''))], 1)
        err = self.assertRaises(errors.RbuildError, self.captureOutput,
                                client.watchImages, [1])
        self.assertEqual(str(err), "rBuilder error Error: ''")

    def testWatchImagesWithBuildName(self):
        client = self._getClient()
        server = client.server
        mock.mock(time, 'sleep')
        server.getBuildStatus._mock.setReturns(
                            [(False, {'message' : 'foo', 'name' : 'qux', 'status' : 0}),
                             (False, {'message' : 'bar', 'name' : 'qux', 'status' : 300})],
                                        1)
        server.getBuildStatus._mock.setReturns(
                            [(False, {'message' : 'bam', 'name' : 'baz', 'status' : 200}),
                             (False, {'message' : 'zap', 'name' : 'baz', 'status' : 500})],
                                        2)
        client.watchImages([1, 2])
        client._handle.ui.info._mock.assertNotCalled()
        client._handle.ui.warning._mock.assertNotCalled()
        client._handle.ui.error._mock.assertNotCalled()
        self.assertEquals(
            [x[0][0]%x[0][1:] for x in client._handle.ui.write._mock.calls],
            ['qux 1: Waiting "foo"',
             'baz 2: Built "bam"',
             'qux 1: Finished "bar"',
             'baz 2: Unknown "zap"',
             'All jobs completed',
             'Finished builds:',
             "    Build 1 ended with 'Finished' status: bar",
             "    Build 2 ended with 'Unknown' status: zap"])

        server.getBuildStatus._mock.setReturns(
                            [(False, {'message' : 'bam', 'name' : 'baz', 'status' : 200}),
                             (True, ('Error', ''))], 1)
        err = self.assertRaises(errors.RbuildError, self.captureOutput,
                                client.watchImages, [1])
        self.assertEqual(str(err), "rBuilder error Error: ''")

    def testWatchImagesSocketTimeout(self):
        client = self._getClient()
        server = client.server
        mock.mock(time, 'sleep')
        import socket
        def foo(*a, **k):
            raise socket.timeout()
        server._mock.set(getBuildStatus=foo)
        err = self.assertRaises(errors.RbuildError, client.watchImages, [1, 2])
        self.assertEquals('rBuilder connection timed out after 3 attempts',
                          err.msg)

    def testWatchImagesStatusTimeout(self):
        client = self._getClient()
        server = client.server
        mock.mock(time, 'sleep')
        self.now = 1000
        def foo():
            self.now += 1
            return self.now
        self.mock(time, 'time', foo)
        server.getBuildStatus._mock.setReturn(
            (False, {'message' : 'bam', 'status' : 200}), 2)
        client.watchImages([2], timeout=30)
        self.assertEquals(
            [x[0][0]%x[0][1:] for x in client._handle.ui.write._mock.calls],
            ['2: Built "bam"',
             "    Last status: Build 2 ended with 'Built' status: bam",
             'Finished builds:'])
        self.assertEquals(
            [x[0][0]%x[0][1:] for x in client._handle.ui.error._mock.calls],
            ['Timed out while waiting for build status to change (30 seconds)'])

    def testGetBuildFiles(self):
        client = self._getClient()
        server = client.server
        server.getBuildFilenames._mock.setReturn( [False,
 [{'downloadUrl': 'http://www.rpath.org/downloadImage?fileId=20588',
   'fileId': 20588,
   'fileUrls': [[40478,
                 1,
                 'http://s3.amazonaws.com/rbuilder/rpath%2F12423%2Frpath-1.0.7-x86-disc1.iso'],
                [40479,
                 2,
                 'http://s3.amazonaws.com/rbuilder/rpath%2F12423%2Frpath-1.0.7-x86-disc1.iso?torrent']],
   'idx': 0,
   'sha1': '511b07104feff5324c8c02321311b576a4af158e',
   'size': '733597696',
   'title': 'rPath Linux Disc 1'},
  {'downloadUrl': 'http://www.rpath.org/downloadImage?fileId=20589',
   'fileId': 20589,
   'fileUrls': [[40480,
                 1,
                 'http://s3.amazonaws.com/rbuilder/rpath%2F12423%2Frpath-1.0.7-x86-disc2.iso'],
                [40481,
                 2,
                 'http://s3.amazonaws.com/rbuilder/rpath%2F12423%2Frpath-1.0.7-x86-disc2.iso?torrent']],
   'idx': 1,
   'sha1': '8a2046e33b039c2136aedc7b2781df17e9789ab4',
   'size': '728041472',
   'title': 'rPath Linux Disc 2'},
  {'downloadUrl': 'http://www.rpath.org/downloadImage?fileId=20590',
   'fileId': 20590,
   'fileUrls': [[40482,
                 1,
                 'http://s3.amazonaws.com/rbuilder/rpath%2F12423%2Fboot.iso'],
                [40483,
                 2,
                 'http://s3.amazonaws.com/rbuilder/rpath%2F12423%2Fboot.iso?torrent']],
   'idx': 2,
   'sha1': '4110078186db232af4d27674f85cd3ecb1322c12',
   'size': '6352896',
   'title': 'boot.iso'},
  {'downloadUrl': 'http://www.rpath.org/downloadImage?fileId=20591',
   'fileId': 20591,
   'fileUrls': [[40484,
                 1,
                 'http://s3.amazonaws.com/rbuilder/rpath%2F12423%2Fdiskboot.img'],
                [40485,
                 2,
                 'http://s3.amazonaws.com/rbuilder/rpath%2F12423%2Fdiskboot.img?torrent']],
   'idx': 3,
   'sha1': '76dca62f95287cfd99ede402625be1be9ba125dd',
   'size': '8388608',
   'title': 'diskboot.img'}]],
                12423
            )
        self.assertEquals(client.getBuildFiles(12423),
            [{'baseFileName': 'rpath-1.0.7-x86-disc1.iso',
              'downloadUrl': 'http://localhost/downloadImage?fileId=20588',
              'fileId': 20588,
              'sha1': '511b07104feff5324c8c02321311b576a4af158e',
              'size': 733597696,
              'title': 'rPath Linux Disc 1',
              'torrentUrl': 'http://localhost/downloadTorrent?fileId=20588'},
             {'baseFileName': 'rpath-1.0.7-x86-disc2.iso',
              'downloadUrl': 'http://localhost/downloadImage?fileId=20589',
              'fileId': 20589,
              'sha1': '8a2046e33b039c2136aedc7b2781df17e9789ab4',
              'size': 728041472,
              'title': 'rPath Linux Disc 2',
              'torrentUrl': 'http://localhost/downloadTorrent?fileId=20589'},
             {'baseFileName': 'boot.iso',
              'downloadUrl': 'http://localhost/downloadImage?fileId=20590',
              'fileId': 20590,
              'sha1': '4110078186db232af4d27674f85cd3ecb1322c12',
              'size': 6352896,
              'title': 'boot.iso',
              'torrentUrl': 'http://localhost/downloadTorrent?fileId=20590'},
             {'baseFileName': 'diskboot.img',
              'downloadUrl': 'http://localhost/downloadImage?fileId=20591',
              'fileId': 20591,
              'sha1': '76dca62f95287cfd99ede402625be1be9ba125dd',
              'size': 8388608,
              'title': 'diskboot.img',
              'torrentUrl': 'http://localhost/downloadTorrent?fileId=20591'}])

        server.getBuildFilenames._mock.setReturn( [True, ('InternalError', 'This error proves the error conditions work')], 12423)
        err = self.assertRaises(errors.RbuildError, client.getBuildFiles, 12423)
        self.assertEquals(err.error, 'InternalError')
        self.assertEquals(err.frozen, 'This error proves the error conditions work')

    def testGetProductId(self):
        client = self._getClient()
        server = client.server
        server.getProjectIdByHostname._mock.setDefaultReturn((False, 42))
        rc = client.getProductId('testproduct')
        assert(rc==42)

        server.getProjectIdByHostname._mock.setDefaultReturn((True, (42,'')))
        self.assertRaises(errors.RbuildError, client.getProductId,
            'testproduct')

        server.getProjectIdByHostname._mock.setDefaultReturn(
            (True, ('ItemNotFound',)))
        self.assertRaises(errors.RbuildError, client.getProductId,
            'testproduct')

    def testCheckAuth(self):
        client = self._getClient()
        server = client.server
        server.checkAuth._mock.setDefaultReturn((False, 1))
        rc = client.checkAuth()
        assert(rc==1)
        server.checkAuth._mock.setDefaultReturn((True, (1, '')))
        self.assertRaises(errors.RbuilderError, client.checkAuth)

    def testShowImageStatus(self):
        client = self._getClient()
        server = client.server
        mock.mock(time, 'sleep')
        server.getBuildStatus._mock.setReturn(
            (False, {'message' : 'foo', 'status' : 0}), 1)
        server.getBuildStatus._mock.setReturn(
            (False, {'message' : 'bam', 'status' : 200}), 2)
        client.showImageStatus([1, 2])
        client._handle.ui.info._mock.assertNotCalled()
        client._handle.ui.warning._mock.assertNotCalled()
        client._handle.ui.error._mock.assertNotCalled()
        self.assertEquals(
            [x[0][0]%x[0][1:] for x in client._handle.ui.write._mock.calls],
            ['1: Waiting "foo"',
             '2: Built "bam"',
             ])

        server.getBuildStatus._mock.setReturn((True, ('Error', '')), 1)
        err = self.assertRaises(errors.RbuildError, self.captureOutput,
            client.watchImages, [1])
        self.assertEqual(str(err), "rBuilder error Error: ''")

    def testPollBuildSocketTimeout(self):
        client = self._getClient()
        server = client.server
        mock.mock(time, 'sleep')
        import socket
        def foo(*a, **k):
            raise socket.timeout()
        server._mock.set(getBuildStatus=foo)
        err = self.assertRaises(errors.RbuildError, client._pollBuild, 1)
        self.assertEquals('rBuilder connection timed out after 3 attempts',
                          err.msg)


class RbuilderRESTClientTest(rbuildhelp.RbuildHelper):
    def setUp(self):
        rbuildhelp.RbuildHelper.setUp(self)

        from rbuild.facade import rbuilderfacade

        mockFinder = mock.MockObject()
        self.mock(rbuilderfacade, 'ApiFinder', mockFinder)

        mockUrl = mock.MockObject()
        mockFinder._mock.setReturn(mockUrl, 'localhost')

        mockUrl3 = mock.MockObject()
        mockUrl3._mock.set(url='http://localhost/api/v1')

        mockUrl2 = mock.MockObject()
        mockUrl2._mock.setReturn(mockUrl3, '')

        mockUrl._mock.set(url=mockUrl2)

    def _getMockResponse(self, content):
        response = StringIO(content)
        return response

    def testAPI(self):
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())
        self.failUnlessEqual(client._api, None)

        mock.mock(robj, 'connect')
        class v1:
            name = 'v1'
        class v2:
            name = 'v2'
        class top:
            api_versions = [v2]

        robj.connect._mock.setReturn(top, 'http://foo:bar@localhost/api')
        err = self.assertRaises(errors.RbuildError, getattr, client, 'api')
        self.assertEqual(str(err), "No compatible REST API found on rBuilder "
                "'http://foo:<PASSWD>@localhost/api'")
        self.assertEqual(client._api, None)

        top.api_versions.append(v1)
        robj.connect._mock.setReturn(top, 'http://foo:bar@localhost/api')
        api = client.api
        self.failIfEqual(client._api, None)
        self.failUnlessEqual(api, v1)

    def testGetGroups(self):
        client = rbuilderfacade.RbuilderRESTClient(
            'http://localhost', 'foo', 'bar', mock.MockObject())
        mock.mock(client, '_api')
        client._api._mock.set(_uri='http://localhost')

        _groups = mock.MockObject()
        client._api._client.do_GET._mock.setReturn(
            _groups, '/products/%s/repos/search?type=group&amp;label=%s' %
                ('test', 'test-1'))
        self.assertEqual(
            client.getGroups('test', 'test-1'), _groups)

        client._api._client.do_GET._mock.raiseErrorOnAccess(
            robj.errors.HTTPNotFoundError(uri=None, status=None, reason=None,
                    response=None))
        err = self.assertRaises(errors.RbuildError, client.getGroups, 'none',
            'none-1')
        self.assertIn("'none'", str(err))
        self.assertIn("'none-1'", str(err))

    def testGetImageTypeDef(self):
        client = rbuilderfacade.RbuilderRESTClient(
            'http://localhost', 'foo', 'bar', mock.MockObject())
        mock.mock(client, '_api')
        client._api._mock.set(_uri='http://localhost')

        _imageTypeDef1 = mock.MockObject()
        _imageTypeDef1.container._mock.set(name='foo')
        _imageTypeDef1.architecture._mock.set(name='bar')
        _imageTypeDef2 = mock.MockObject()
        _imageTypeDef2.container._mock.set(name='spam')
        _imageTypeDef2.architecture._mock.set(name='eggs')

        client._api._client.do_GET._mock.setReturn(
            [_imageTypeDef2, _imageTypeDef1],
            '/products/baz/versions/1/imageTypeDefinitions')
        self.assertEqual(
            client.getImageTypeDef('baz', '1', 'foo', 'bar'), _imageTypeDef1)

        client._api._client.do_GET._mock.raiseErrorOnAccess(
            robj.errors.HTTPNotFoundError(uri=None, status=None, reason=None,
                                          response=None))
        err = self.assertRaises(
            errors.RbuildError,
            client.getImageTypeDef,
            'none',
            'none',
            'foo',
            'bar',
            )
        self.assertIn('not found', str(err))

        err = self.assertRaises(
            errors.RbuildError,
            client.getImageTypeDef,
            'baz',
            '1',
            'none',
            'none',
            )
        self.assertIn("No image type", str(err))

    def testGetImageDefs(self):
        client = rbuilderfacade.RbuilderRESTClient(
            'http://localhost', 'foo', 'bar', mock.MockObject())
        mock.mock(client, '_api')
        client._api._mock.set(_uri='http://localhost')

        _imageDef1 = mock.MockObject()
        _imageDef1._mock.set(id='foo')
        _imageDef1._mock.set(name='bar')
        _imageDef2 = mock.MockObject()
        _imageDef2._mock.set(id='spam')
        _imageDef2._mock.set(name='eggs')

        client._api._client.do_GET._mock.setReturn(
            [_imageDef2, _imageDef1],
            '/products/baz/versions/1/imageDefinitions')

        self.assertEqual(
            client.getImageDefs('baz', '1'), [_imageDef2, _imageDef1])
        self.assertEqual(
            client.getImageDefs('baz', '1', id='foo'), [_imageDef1])
        self.assertEqual(
            client.getImageDefs('baz', '1', name='eggs'), [_imageDef2])

        client._api._client.do_GET._mock.raiseErrorOnAccess(
            robj.errors.HTTPNotFoundError(uri=None, status=None, reason=None,
                                          response=None))
        err = self.assertRaises(
            errors.RbuildError,
            client.getImageDefs,
            'none',
            'none',
            )
        self.assertIn('not found', str(err))

    def testGetProductDefinitionSchemaVersion(self):
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())
        client._api = mock.MockObject()

        # no REST api case
        client._api._mock.set(proddefSchemaVersion=None)
        client._api._mock.set(version_info=None)
        e = self.assertRaises(errors.RbuildError, client.getProductDefinitionSchemaVersion)
        self.assertEquals(e.msg, 'Unable to determine the product definition version offered by rBuilder')

        # pre 5.2.3 api
        client._api._mock.set(proddefSchemaVersion='2.0')
        client._api._mock.set(version_info=None)
        result = client.getProductDefinitionSchemaVersion()
        self.failUnlessEqual(result, '2.0')

        # 5.2.3 > 6.1.0
        client._api._mock.set(proddefSchemaVersion='3.0')
        client._api._mock.set(version_info=None)
        result = client.getProductDefinitionSchemaVersion()
        self.failUnlessEqual(result, '3.0')

        # 6.1.0 and later
        vinfo = mock.MockObject()
        vinfo._mock.set(product_definition_schema_version='4.3')
        client._api._mock.set(version_info=vinfo)
        client._api._mock.set(proddefSchemaVersion=None)
        result = client.getProductDefinitionSchemaVersion()
        self.failUnlessEqual(result, '4.3')

    def testGetWindowsBuildService(self):
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())
        mock.mock(client, '_api')
        client._api._mock.set(inventory=mock.MockObject())

        notwbs = mock.MockObject(system_type=mock.MockObject(
            name='foobar'))

        # Correct WBS system.
        wbs = mock.MockObject(system_type=mock.MockObject(
            name='infrastructure-windows-build-node'),
            networks=[mock.MockObject(ip_address='1.2.3.4',
                                      dns_name='foo.example.com'), ])
        client._api.inventory._mock.set(infrastructure_systems=[wbs, notwbs])
        address = client.getWindowsBuildService()
        self.failUnlessEqual(address, '1.2.3.4')

        # No WBS systems found.
        wbs2 = mock.MockObject(system_type=mock.MockObject(name='bar'))
        client._api.inventory._mock.set(infrastructure_systems=[wbs2, notwbs])
        self.failUnlessRaises(errors.RbuildError, client.getWindowsBuildService)

        # Selected WBS system doesn't have any networks.
        wbs3 = mock.MockObject(system_type=mock.MockObject(
            name='infrastructure-windows-build-node'),
            networks=[])
        client._api.inventory._mock.set(infrastructure_systems=[wbs3, notwbs])
        self.failUnlessRaises(errors.RbuildError, client.getWindowsBuildService)

    def testConfigureTarget(self):
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())
        mock.mock(client, '_api')
        job = mock.MockObject()
        job.job_state._mock.set(name='Completed')
        _jobs = []
        def _append(x):
            _jobs.append(x)
            return job
        target = mock.MockObject()
        target.jobs._mock.set(append=_append)
        ddata = mock.MockObject()
        ddata._mock.set(toxml=lambda: '<descriptor_data/>')
        results = client.configureTarget(target, ddata)
        self.assertEqual(results, target)
        self.assertTrue(len(_jobs) == 1)

        job.job_state._mock.set(name='Failed')
        job._mock.set(status_text='failed for some reason')
        err = self.assertRaises(
            errors.RbuildError, client.configureTarget, target, ddata)
        self.assertEqual('failed for some reason', str(err))
        self.assertTrue(len(_jobs) == 2)

    def testConfigureTargetCredentials(self):
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())
        mock.mock(client, '_api')
        job = mock.MockObject()
        job.job_state._mock.set(name='Completed')
        _jobs = []
        def _append(x):
            _jobs.append(x)
            return job
        target = mock.MockObject()
        target.jobs._mock.set(append=_append)
        ddata = mock.MockObject()
        ddata._mock.set(toxml=lambda: '<descriptor_data/>')
        results = client.configureTargetCredentials(target, ddata)
        self.assertEqual(results, target)
        self.assertTrue(len(_jobs) == 1)

        job.job_state._mock.set(name='Failed')
        self.assertRaises(
            errors.RbuildError, client.configureTarget, target, ddata)
        self.assertTrue(len(_jobs) == 2)

    def testCreateProject(self):
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())
        mock.mock(client, '_api')
        class response:
            project_id = 42
        client._api.projects.append._mock.setDefaultReturn(response)
        projectId = client.createProject('title', 'shortname', 'hostname', 'domain.name')
        self.assertEqual(projectId, 42)
        proj = client._api.projects.append._mock.popCall()[0][0].project
        self.assertEqual(proj.name, 'title')
        self.assertEqual(proj.hostname, 'hostname')
        self.assertEqual(proj.short_name, 'shortname')
        self.assertEqual(proj.domain_name, 'domain.name')
        self.assertEqual(proj.external, 'false')

        client._api.projects.append._mock.raiseErrorOnAccess(
                robj.errors.HTTPConflictError(uri=None, status=None,
                    reason=None, response=None))
        err = self.assertRaises(errors.RbuildError, client.createProject, 'title', 'shortname', 'hostname', 'domain.name')
        self.assertIn('conflicting', str(err))

    def testCreateExternalProject(self):
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())
        mock.mock(client, '_api')
        class response:
            project_id = 42
        client._api.projects.append._mock.setDefaultReturn(response)
        projectId = client.createProject(
            'title', 'shortname', 'hostname',
            'domain.name', 'description', True, (['repo@n:branch'],
                'otherdomain.name', 'auth', 'user', 'secret', 'entitle'))
        self.assertEqual(projectId, 42)
        proj = client._api.projects.append._mock.popCall()[0][0].project
        self.assertEqual(proj.name, 'title')
        self.assertEqual(proj.hostname, 'hostname')
        self.assertEqual(proj.short_name, 'shortname')
        self.assertEqual(proj.domain_name, 'domain.name')
        self.assertEqual(proj.description, 'description')
        self.assertEqual(proj.external, 'true')
        self.assertEqual(proj.labels, ['repo@n:branch'])
        self.assertEqual(proj.upstream_url, 'otherdomain.name')
        self.assertEqual(proj.auth_type, 'auth')
        self.assertEqual(proj.user_name, 'user')
        self.assertEqual(proj.password, 'secret')
        self.assertEqual(proj.entitlement, 'entitle')

    def testCreateTarget(self):
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())
        mock.mock(client, '_api')
        _targets = []
        def _append(x, tag=None):
            _targets.append(x)
            return x

        client._api.targets._mock.set(append=_append)
        _ddata = {
            'name': 'foo',
            'zone': 'local',
            'description': 'Foo',
            }
        ddata = mock.MockObject()
        ddata._mock.set(getField=lambda x: _ddata[x])

        expected_results = xobj.parse(TARGET_XML)

        results = client.createTarget("vmware", ddata)
        self.assertEqual(results.toxml(), expected_results.toxml())
        self.assertTrue(len(_targets) == 1)

        def _append_error(x, tag=None):
            raise robj.errors.HTTPConflictError(
                uri=None, status=None, reason=None, response=None)

        client._api.targets._mock.set(append=_append_error)
        self.assertRaises(
            errors.RbuildError, client.createTarget, "vmware", ddata)
        self.assertTrue(len(_targets) == 1)

    def testGetImageTypes(self):
        client = rbuilderfacade.RbuilderRESTClient(
            'http://localhost', 'foo', 'bar', mock.MockObject())
        mock.mock(client, '_getResources')
        client._getResources._mock.setReturn(['foo', 'bar'], 'image_types')
        client._getResources._mock.setReturn(['foo'], 'image_types', name='foo')
        client._getResources._mock.setReturn(['foo'], 'image_types', name='foo')
        self.assertEqual(client.getImageTypes(), ['foo', 'bar'])
        self.assertEqual(client.getImageTypes(name='foo'), ['foo'])

    def testGetProject(self):
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
                'bar', mock.MockObject())
        mock.mock(client, '_api')
        client._api._mock.set(_uri='http://localhost')

        client._api._client.do_GET._mock.setReturn('response',
                'http://localhost/projects/foo')
        self.assertEqual(client.getProject('foo'), 'response')

        client._api._client.do_GET._mock.raiseErrorOnAccess(
                robj.errors.HTTPNotFoundError(uri=None, status=None,
                    reason=None, response=None))
        err = self.assertRaises(errors.RbuildError, client.getProject, 'bar')
        self.assertIn('not found', str(err))

    def testGetTargetTypes(self):
        TargetType = namedtuple('TargetType', 'name value')

        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())

        mock.mockMethod(client._getResources, [
            TargetType('vmware', 'VMWare'),
            TargetType('ec2', 'Amazon EC2'),
            ])

        results = client.getTargetTypes()
        self.assertEqual(results, [
            TargetType('vmware', 'VMWare'),
            TargetType('ec2', 'Amazon EC2'),
            ])

    def testCreateBranch(self):
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())
        mock.mock(client, '_api')
        proj = mock.MockObject()
        proj._mock.set(id='id', name='proj', short_name='short',
                domain_name='dom')
        mock.mockMethod(client.getProject)
        client.getProject._mock.setReturn(proj, 'proj')

        client.createBranch('proj', 'branch', 'plat', 'nsp', 'desc')
        xml = proj.project_branches.append._mock.popCall()[0][0].project_branch
        self.assertEqual(xml.name, 'branch')
        self.assertEqual(xml.platform_label, 'plat')
        self.assertEqual(xml.description, 'desc')
        self.assertEqual(xml.namespace, 'nsp')
        self.assertEqual(xml.project.id, 'id')

    def testCreateExistingBranch(self):
        '''Regression test for APPENG-2790'''
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())
        mock.mock(client, '_api')
        br = mock.MockObject()
        br._mock.set(name='branch')
        _project_branches = mock.MockObject()
        _project_branches._mock.disable('__iter__')
        _project_branches.__iter__._mock.raiseErrorOnAccess(
            TypeError("A list type is required for this method."))
        proj = mock.MockObject()
        proj._mock.set(id='id', name='proj', short_name='short',
                domain_name='dom', project_branches=[br])
        mock.mockMethod(client.getProject)
        client.getProject._mock.setReturn(proj, 'proj')

        err = self.assertRaises(
            errors.RbuildError,
            client.createBranch,
            'proj', 'branch', 'plat', 'nsp', 'desc',
            )
        self.assertIn('already exists', str(err))

    def testCreateFirstBranch(self):
        '''Regression test for APPENG-2790: no existing branches'''
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())
        mock.mock(client, '_api')
        _project_branches = mock.MockObject()
        _project_branches._mock.disable('__iter__')
        _project_branches.__iter__._mock.raiseErrorOnAccess(
            TypeError("A list type is required for this method."))
        proj = mock.MockObject()
        proj._mock.set(id='id', name='proj', short_name='short',
                domain_name='dom', project_branches=_project_branches)
        mock.mockMethod(client.getProject)
        client.getProject._mock.setReturn(proj, 'proj')

        client.createBranch('proj', 'branch', 'plat', 'nsp', 'desc')
        xml = proj.project_branches.append._mock.popCall()[0][0].project_branch
        self.assertEqual(xml.name, 'branch')
        self.assertEqual(xml.platform_label, 'plat')
        self.assertEqual(xml.description, 'desc')
        self.assertEqual(xml.namespace, 'nsp')
        self.assertEqual(xml.project.id, 'id')

    def testListPlatforms(self):
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())
        mock.mock(client, '_api')
        Platform = namedtuple('Platform',
                'enabled hidden abstract platformName label')
        client._api.platforms._mock.set(platform=[
            Platform('true',  'false', 'false', 'plat1', 'plat@1'),
            Platform('false', 'false', 'false', 'plat2', 'plat@2'),
            Platform('true',  'true',  'false', 'plat3', 'plat@3'),
            Platform('true',  'false', 'true',  'plat4', 'plat@4'),
            ])
        results = client.listPlatforms()
        self.assertEqual(results, [Platform('true', 'false', 'false', 'plat1', 'plat@1')])

    def testGetTarget(self):
        client = rbuilderfacade.RbuilderRESTClient(
            'http://localhost', 'foo', 'bar', mock.MockObject())
        mock.mock(client, '_api')
        client._api._mock.set(_uri='http://localhost')
        client._api._client.do_GET._mock.setReturn(
            ['target'],
            "http://localhost/targets;filter_by=[name,EQUAL,foo]")
        client._api._client.do_GET._mock.setReturn(
            [],
            "http://localhost/targets;filter_by=[name,EQUAL,bar]")

        self.assertEqual(client.getTarget('foo'), 'target')

        err = self.assertRaises(errors.RbuildError, client.getTarget, 'bar')
        self.assertIn('not found', str(err))

    def testGetTargets(self):
        client = rbuilderfacade.RbuilderRESTClient(
            'http://localhost', 'foo', 'bar', mock.MockObject())
        mock.mock(client, '_getResources')
        client._getResources._mock.setReturn(['foo', 'bar'], 'targets')
        client._getResources._mock.setReturn(['foo'], 'targets', name='foo')
        client._getResources._mock.setReturn(['foo'], 'targets', name='foo')
        self.assertEqual(client.getTargets(), ['foo', 'bar'])
        self.assertEqual(client.getTargets(name='foo'), ['foo'])

    def testGetImages(self):
        client = rbuilderfacade.RbuilderRESTClient(
            'http://localhost', 'foo', 'bar', mock.MockObject())
        mock.mock(client, '_api')
        client._api._mock.set(_uri='http://localhost')

        err = self.assertRaises(
            errors.RbuildError, client.getImages, 'foo', stage='bar')
        self.assertIn('Must provide', str(err))

        _project = mock.MockObject()
        _project._mock.set(id='http://localhost/projects/bar')

        client._api._client.do_GET._mock.setReturn(
            _project, 'http://localhost/projects/bar')
        client._api._client.do_GET._mock.setReturn(
            'image',
            "http://localhost/images"
                ';filter_by=AND(EQUAL(name,"foo"))'
                ";order_by=-time_created")
        client._api._client.do_GET._mock.setReturn(
            'image_version',
            "http://localhost/images"
                ';filter_by=AND(EQUAL(trailing_version,"1-1-1")'
                ',EQUAL(name,"foo"))'
                ";order_by=-time_created")
        client._api._client.do_GET._mock.setReturn(
            'project',
            "http://localhost/projects/bar/images"
                ';filter_by=AND(EQUAL(name,"foo"))'
                ";order_by=-time_created")
        client._api._client.do_GET._mock.setReturn(
            'project_stage',
            "http://localhost/projects/bar/project_branches/baz/project_branch_stages/Release/images"
                ';filter_by=AND(EQUAL(name,"foo"))'
                ";order_by=-time_created")
        client._api._client.do_GET._mock.setReturn(
            'project_stage_version',
            "http://localhost/projects/bar/project_branches/baz/project_branch_stages/Release/images"
                ';filter_by=AND(EQUAL(trailing_version,"1-1-1")'
                ',EQUAL(name,"foo"))'
                ";order_by=-time_created")
        client._api._client.do_GET._mock.setReturn(
            [],
            'http://localhost/images;filter_by=AND(EQUAL(name,"bar"))'
                ";order_by=-time_created")

        self.assertEqual(client.getImages('foo'), 'image')
        self.assertEqual(
            client.getImages('foo', trailingVersion='1-1-1'), 'image_version')
        self.assertEqual(client.getImages('foo', project='bar'), 'project')
        self.assertEqual(
            client.getImages('foo', project='bar', branch='baz',
                             stage='Release'),
            'project_stage')
        self.assertEqual(
            client.getImages(
                'foo',
                project='bar',
                branch='baz',
                stage='Release',
                trailingVersion='1-1-1',
                ),
            'project_stage_version')

        self.assertEqual(client.getImages('bar'), [])

    def test_getResources(self):
        client = rbuilderfacade.RbuilderRESTClient(
            'http://localhost', 'foo', 'bar', mock.MockObject())
        mock.mock(client, '_api')
        client._api._mock.set(_uri='http://localhost')

        client._api._client.do_GET._mock.setReturn(
            'projects', 'http://localhost/projects')

        client._api._client.do_GET._mock.setReturn(
            'projects_filtered',
            "http://localhost/projects"
                ';filter_by=AND(EQUAL(name,"foo"))',
            )
        client._api._client.do_GET._mock.setReturn(
            'projects_ordered',
            "http://localhost/projects"
                ";order_by=name",
            )
        client._api._client.do_GET._mock.setReturn(
            'projects_ordered_filtered',
            "http://localhost/projects"
                ';filter_by=AND(EQUAL(name,"foo"))'
                ";order_by=name",
            )
        client._api._client.do_GET._mock.setReturn(
            'custom_uri',
            "http://localhost/foo/bar/projects",
            )

        self.assertEqual(client._getResources('projects'), 'projects')

        self.assertEqual(
            client._getResources('projects', order_by='name'),
            'projects_ordered',
            )
        self.assertEqual(
            client._getResources('projects', name='foo'),
            'projects_filtered',
            )
        self.assertEquals(
            client._getResources('projects', name='foo', order_by='name'),
            'projects_ordered_filtered',
            )

        self.assertEquals(
            client._getResources('projects', uri='/foo/bar/'),
            'custom_uri',
            )

        self.assertEquals(
            client._getResources('projects', uri='foo/bar/'),
            'custom_uri',
            )

        self.assertEquals(
            client._getResources('projects', uri='/foo/bar'),
            'custom_uri',
            )

        client._api._client.do_GET._mock.raiseErrorOnAccess(
            robj.errors.HTTPNotFoundError(uri='foo', status='404',
                                          reason='', response=''))
        err = self.assertRaises(
            errors.RbuildError, client._getResources, 'projects')
        self.assertIn('Unable to fetch', str(err))
