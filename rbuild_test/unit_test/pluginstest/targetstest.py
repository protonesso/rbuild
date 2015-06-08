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

from StringIO import StringIO

from rbuild import errors
from testutils import mock

from rbuild_test import rbuildhelp


class AbstractTargetTest(rbuildhelp.RbuildHelper):
    def setUp(self):
        rbuildhelp.RbuildHelper.setUp(self)
        self.handle = self.getRbuildHandle(mock.MockObject())
        self.handle.Create.registerCommands()
        self.handle.Delete.registerCommands()
        self.handle.Edit.registerCommands()
        self.handle.List.registerCommands()
        self.handle.Targets.registerCommands()
        self.handle.Create.initialize()
        self.handle.Delete.initialize()
        self.handle.Edit.initialize()
        self.handle.List.initialize()
        self.handle.Targets.initialize()


class CreateTargetTest(AbstractTargetTest):
    def testCreateTargetArgParse(self):
        self.checkRbuild(
            'create target --from-file=file --to-file=toFile vmware',
            'rbuild_plugins.targets.CreateTargetCommand.runCommand',
            [None, None, {
                'from-file': 'file',
                'to-file': 'toFile',
                }, ['create', 'target', 'vmware']])

    def testCreateTargetCmdline(self):
        handle = self.handle

        mock.mockMethod(handle.DescriptorConfig.readConfig)
        mock.mockMethod(handle.DescriptorConfig.writeConfig)
        mock.mockMethod(handle.facade.rbuilder.getTargetTypes)
        mock.mockMethod(handle.Targets.createTarget)
        mock.mockMethod(handle.Targets.configureTargetCredentials)

        handle.Targets.createTarget._mock.setReturn('target', "vmware")

        cmd = handle.Commands.getCommandClass('create')()

        err = self.assertRaises(
            errors.ParseError,
            cmd.runCommand,
            handle,
            {},
            ['rbuild', 'create', 'target'],
            )
        self.assertEqual(
            str(err), "'target' missing 1 command parameter(s): TYPE")

        cmd.runCommand(
            handle,
            {'list': False},
            ['rbuild', 'create', 'target', 'vmware'],
            )
        handle.DescriptorConfig.readConfig._mock.assertNotCalled()
        handle.Targets.createTarget._mock.assertCalled("vmware")
        handle.Targets.configureTargetCredentials\
            ._mock.assertCalled('target')

        cmd.runCommand(
            handle,
            {'list': False, 'from-file': 'foo'},
            ['rbuild', 'create', 'target', 'vmware'],
            )
        handle.DescriptorConfig.readConfig._mock.assertCalled('foo')
        handle.Targets.createTarget._mock.assertCalled("vmware")
        handle.Targets.configureTargetCredentials\
            ._mock.assertCalled('target')
        handle.DescriptorConfig.writeConfig._mock.assertNotCalled()

        cmd.runCommand(
            handle,
            {'list': False, 'to-file': 'foo'},
            ['rbuild', 'create', 'target', 'vmware'],
            )
        handle.DescriptorConfig.readConfig._mock.assertNotCalled()
        handle.Targets.createTarget._mock.assertCalled("vmware")
        handle.Targets.configureTargetCredentials\
            ._mock.assertCalled('target')
        handle.DescriptorConfig.writeConfig._mock.assertCalled('foo')


class DeleteTargetTest(AbstractTargetTest):
    def testDeleteTargetArgParse(self):
        self.checkRbuild(
            'delete targets --force vmware',
            'rbuild_plugins.targets.DeleteTargetsCommand.runCommand',
            [None, None, {"force": True}, ['delete', 'targets', 'vmware']])

    def testDeleteTargetCmdline(self):
        handle = self.handle

        mock.mockMethod(handle.Targets.delete)

        cmd = handle.Commands.getCommandClass('delete')()

        err = self.assertRaises(
            errors.ParseError,
            cmd.runCommand,
            handle,
            {},
            ['rbuild', 'delete', 'targets'],
            )
        self.assertEqual(
            str(err), "'targets' missing 1 command parameter(s): TARGET")

        cmd.runCommand(handle, {"force": True},
                       ['rbuild', 'delete', 'targets', 'foo'])
        handle.Targets.delete._mock.assertCalled("foo", True)

        cmd.runCommand(handle, {}, ['rbuild', 'delete', 'targets', 'foo'])
        handle.Targets.delete._mock.assertCalled("foo", False)


class EditTargetTest(AbstractTargetTest):
    def testEditTargetArgParse(self):
        self.checkRbuild(
            'edit target --from-file=file --to-file=toFile foo',
            'rbuild_plugins.targets.EditTargetCommand.runCommand',
            [None, None, {
                'from-file': 'file',
                'to-file': 'toFile',
                }, ['edit', 'target', 'foo']])

    def testEditTargetCmdLine(self):
        handle = self.handle

        mock.mockMethod(handle.DescriptorConfig.readConfig)
        mock.mockMethod(handle.DescriptorConfig.writeConfig)
        mock.mockMethod(handle.Targets.edit)
        handle.Targets.edit

        cmd = handle.Commands.getCommandClass('edit')()

        err = self.assertRaises(
            errors.ParseError,
            cmd.runCommand,
            handle,
            dict(),
            ['rbuild', 'edit', 'target'],
            )
        self.assertEqual(
            str(err), "'target' missing 1 command parameter(s): NAME")

        cmd.runCommand(
            handle,
            dict(),
            ['rbuild', 'edit', 'target', '1'],
            )
        handle.DescriptorConfig.readConfig._mock.assertNotCalled()
        handle.Targets.edit._mock.assertCalled('1', None)

        cmd.runCommand(
            handle,
            dict(),
            ['rbuild', 'edit', 'target', '1', '2'],
            )
        handle.DescriptorConfig.readConfig._mock.assertNotCalled()
        handle.Targets.edit._mock.assertCalled('1', '2')

        cmd.runCommand(
            handle,
            {'from-file': 'foo'},
            ['rbuild', 'edit', 'target', '1'],
            )
        handle.DescriptorConfig.readConfig._mock.assertCalled('foo')
        handle.Targets.edit._mock.assertCalled('1', None)
        handle.DescriptorConfig.writeConfig._mock.assertNotCalled()

        cmd.runCommand(
            handle,
            {'to-file': 'foo'},
            ['rbuild', 'edit', 'target', '1'],
            )
        handle.DescriptorConfig.readConfig._mock.assertNotCalled()
        handle.Targets.edit._mock.assertCalled('1', None)
        handle.DescriptorConfig.writeConfig._mock.assertCalled('foo')


class ListTargetsTest(AbstractTargetTest):
    def testCommandParsing(self):
        handle = self.handle
        cmd = handle.Commands.getCommandClass('list')()

        mock.mockMethod(handle.Targets.list)

        cmd.runCommand(handle, {}, ['rbuild', 'list', 'targets'])
        handle.Targets.list._mock.assertCalled()

    def testCommand(self):
        self.checkRbuild('list targets',
            'rbuild_plugins.targets.ListTargetsCommand.runCommand',
            [None, None, {}, ['list', 'targets']])


class TargetsPluginTest(AbstractTargetTest):
    def testEdit(self):
        h = self.handle

        mock.mock(h, 'DescriptorConfig')
        mock.mock(h.facade, 'rbuilder')
        mock.mock(h, 'ui')

        mock.mockMethod(h.Targets.configureTargetCredentials)
        mock.mockMethod(h.getConfig)

        rb = h.facade.rbuilder

        # mock out target fetching
        _target = mock.MockObject()
        _target.target_configuration._mock.set(elements=list())
        _target.target_type._mock.set(name='type')

        _desc = mock.MockObject()
        _ddata = mock.MockObject()
        _ttype = mock.MockObject(
            name="type",
            descriptor_create_target=StringIO("descriptor xml"),
            )

        rb.getTargets._mock.setReturn([_target], name='foo')
        rb.getTargetTypes._mock.setReturn([_ttype])
        h.DescriptorConfig.createDescriptorData._mock.setReturn(_ddata,
            fromStream="descriptor xml", defaults={})
        rb.configureTarget._mock.setReturn(_target, _target, _ddata)

        # no target 'bar'
        rb.getTargets._mock.setReturn(None, name='bar')

        err = self.assertRaises(errors.PluginError, h.Targets.edit, 'bar')
        self.assertEqual("No target found with name 'bar'", str(err))

        _config = mock.MockObject()
        h.getConfig._mock.setReturn(_config)
        rb.isAdmin._mock.setReturn(True, 'admin')
        rb.isAdmin._mock.setReturn(False, 'user')

        # user is not admin
        _config._mock.set(user=('user', 'secret'))
        h.Targets.edit('foo')
        rb.configureTarget._mock.assertNotCalled()
        h.Targets.configureTargetCredentials._mock.assertCalled(_target)

        # user is admin
        _config._mock.set(user=('admin', 'secret'))
        h.Targets.edit('foo')
        rb.configureTarget._mock.assertCalled(_target, _ddata)
        h.Targets.configureTargetCredentials._mock.assertCalled(_target)

    def testList(self):
        handle = self.handle

        mock.mockMethod(handle.facade.rbuilder.getTargets)

        handle.Targets.list()
        handle.facade.rbuilder.getTargets._mock.assertCalled()

    def testCreate(self):
        handle = self.handle

        _ddata = mock.MockObject()
        _ttype = mock.MockObject(
            name="type",
            descriptor_create_target=StringIO("descriptor"),
            )

        mock.mock(handle, "DescriptorConfig")
        handle.DescriptorConfig.createDescriptorData._mock.setReturn(
            _ddata, fromStream="descriptor", defaults=dict())

        mock.mock(handle.facade, "rbuilder")
        handle.facade.rbuilder.getTargetTypes._mock.setReturn([_ttype])
        handle.facade.rbuilder.createTarget._mock.setReturn(
            "target", _ttype.name, _ddata)

        err = self.assertRaises(
            errors.PluginError,
            handle.Targets.createTarget,
            "notype"
            )
        self.assertEqual(str(err), "No such target type 'notype'. Run"
            " `rbuild list targettypes` to see valid target types")

        rv = handle.Targets.createTarget("type")
        self.assertEqual(rv, "target")

    def testConfigurationFailsDuringCreate(self):
        handle = self.handle

        _ddata = mock.MockObject()
        _ttype = mock.MockObject(
            name="type",
            descriptor_create_target=StringIO("descriptor"),
            )
        _target = mock.MockObject(
            name="target"
            )

        mock.mock(handle, "DescriptorConfig")
        handle.DescriptorConfig.createDescriptorData._mock.setReturn(
            _ddata, fromStream="descriptor", defaults=dict())

        mock.mock(handle.facade, "rbuilder")
        handle.facade.rbuilder.getTargetTypes._mock.setReturn([_ttype])
        handle.facade.rbuilder.createTarget._mock.setReturn(
            _target, _ttype.name, _ddata)
        def raisesRbuildError(self, target):
            raise errors.RbuildError("Can't configure target: foo")
        handle.facade.rbuilder._mock.set(configureTarget=raisesRbuildError)
        mock.mock(handle.ui, 'warning')
        mock.mock(handle.ui, 'getYn')
        # attempt to edit one time, then stop
        handle.ui.getYn._mock.setReturns([True, False], "Edit target again?", default=False)
        _ddata.getFields._mock.setReturn(dict())

        from rbuild_plugins import targets # not sure why this can't be imported at the top

        err = self.assertRaises(
            targets.TargetNotCreated,
            handle.Targets.createTarget,
            "type"
            )
        self.assertEqual(str(err), "Target 'target' not created")
        # target deleted twice
        _target.delete._mock.assertCalled()
        _target.delete._mock.assertCalled()
        # warning issued twice
        handle.ui.warning._mock.assertCalled("Can't configure target: foo")
        handle.ui.warning._mock.assertCalled("Can't configure target: foo")

    def testDelete(self):
        handle = self.handle

        _target1 = mock.MockObject(name="foo", id="1")
        _target2 = mock.MockObject(name="bar", id="2")
        mock.mockMethod(handle.facade.rbuilder.getTargets)
        handle.facade.rbuilder.getTargets._mock.setReturn(
            [_target1, _target2])
        handle.facade.rbuilder.getTargets._mock.appendReturn(
            [_target1], target_id="1")
        handle.facade.rbuilder.getTargets._mock.appendReturn(
            [], target_id="bar")

        mock.mock(handle, "ui")
        handle.ui.getYn._mock.setDefaultReturn(False)
        handle.ui.getYn._mock.setReturn(True, "Delete foo?", default=False)
        handle.ui.getYn._mock.setReturn(True, "Delete bar?", default=False)


        handle.Targets.delete("1", force=True)
        handle.facade.rbuilder.getTargets._mock.assertCalled(target_id="1")
        handle.ui.getYn._mock.assertNotCalled()
        _target1.delete._mock.assertCalled()

        handle.Targets.delete("1")
        handle.facade.rbuilder.getTargets._mock.assertCalled(target_id="1")
        handle.ui.getYn._mock.assertCalled("Delete foo?", default=False)
        _target1.delete._mock.assertCalled()

        handle.Targets.delete("bar")
        handle.facade.rbuilder.getTargets._mock.assertCalled(target_id="bar")
        handle.facade.rbuilder.getTargets._mock.assertCalled()
        handle.ui.getYn._mock.assertCalled("Delete bar?", default=False)
        _target2.delete._mock.assertCalled()
