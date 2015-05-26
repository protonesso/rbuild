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

from rbuild import errors
from testutils import mock

from rbuild_test import rbuildhelp


DESCRIPTOR_XML = '''\
<descriptor xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.rpath.com/permanent/descriptor-1.1.xsd" xsi:schemaLocation="http://www.rpath.com/permanent/descriptor-1.1.xsd descriptor-1.1.xsd" version="1.1">
    <metadata>
        <displayName>VMware Image Upload Parameters</displayName>
        <rootElement>descriptor_data</rootElement>
        <descriptions>
            <desc>VMware Image Upload Parameters</desc>
        </descriptions>
    </metadata>
    <dataFields>
        <field>
            <name>name</name>
            <descriptions>
                <desc>Name</desc>
            </descriptions>
            <type>str</type>
            <constraints>
                <length>4</length>
            </constraints>
            <required>true</required>
            <hidden>false</hidden>
        </field>
    </dataFields>
</descriptor>
'''

DDATA_XML = '''\
<?xml version='1.0' encoding='UTF-8'?>
<descriptor_data>
    <tag>foo</tag>
</descriptor_data>
'''

JOB_XML = '''\
<?xml version='1.0' encoding='UTF-8'?>
<job>
  <descriptor>descriptor</descriptor>
  <descriptor_data>
    <tag>foo</tag>
  </descriptor_data>
  <job_type>job_type</job_type>
</job>
'''


class AbstractImagesTest(rbuildhelp.RbuildHelper):
    def setUp(self):
        rbuildhelp.RbuildHelper.setUp(self)
        self.handle = self.getRbuildHandle(mock.MockObject())
        self.handle.Cancel.registerCommands()
        self.handle.Delete.registerCommands()
        self.handle.List.registerCommands()
        self.handle.Show.registerCommands()
        self.handle.Images.registerCommands()
        self.handle.Cancel.initialize()
        self.handle.Delete.initialize()
        self.handle.List.initialize()
        self.handle.Show.initialize()
        self.handle.Images.initialize()


class CancelImagesTest(AbstractImagesTest):
    def setUp(self):
        AbstractImagesTest.setUp(self)
        self.cmd = self.handle.Commands.getCommandClass('cancel')()

    def testCommand(self):
        self.checkRbuild('cancel images',
            'rbuild_plugins.images.CancelImagesCommand.runCommand',
            [None, None, {}, ['cancel', 'images']])
        self.checkRbuild('cancel images 1 2',
            'rbuild_plugins.images.CancelImagesCommand.runCommand',
            [None, None, {}, ['cancel', 'images', '1', '2']])

    def testCommandParsing(self):
        handle = self.handle

        mock.mockMethod(handle.Images.cancel)
        mock.mockMethod(handle.ui.warning)
        mock.mockMethod(handle.facade.rbuilder.getImages, ['image'])

        err = self.assertRaises(
            errors.ParseError, self.cmd.runCommand, handle, {},
            ['rbuild', 'cancel', 'images'])
        self.assertIn(': id', str(err))

        self.cmd.runCommand(handle, {}, ['rbuild', 'cancel', 'images', '10'])
        handle.Images.cancel._mock.assertCalled('image')

        err = self.assertRaises(errors.BadParameterError,
            self.cmd.runCommand, handle, {},
            ['rbuild', 'cancel', 'images', '&^%&*%$^&$'])
        self.assertIn('Cannot parse', str(err))

    def testLaunchArgParse(self):
        self.checkRbuild('cancel images 10',
            'rbuild_plugins.images.CancelImagesCommand.runCommand',
            [None, None, {}, ['cancel', 'images', '10']])

    def testNoImage(self):
        from rbuild_plugins import images

        mock.mockMethod(self.handle.Images.cancel)
        mock.mockMethod(self.handle.Images._getProductStage,
            ('project', 'branch', 'stage'))
        mock.mockMethod(self.handle.ui.warning)
        mock.mockMethod(self.handle.ui.getYn, True)
        mock.mockMethod(self.handle.facade.rbuilder.getImages, None)

        self.cmd.runCommand(self.handle, {},
            ['rbuild', 'cancel', 'images', '10'])
        self.handle.ui.warning._mock.assertCalled("Unable to find image with"
            " id '10' on stage stage of project project")
        self.handle.Images.cancel._mock.assertNotCalled()


class DeleteImagesTest(AbstractImagesTest):
    def testCommandParsing(self):
        handle = self.handle
        cmd = handle.Commands.getCommandClass('delete')()

        mock.mockMethod(handle.Images.delete)
        mock.mockMethod(handle.ui.warning)

        err = self.assertRaises(
            errors.ParseError, cmd.runCommand, handle, {},
            ['rbuild', 'delete', 'images'])
        self.assertIn('IMAGEID', str(err))

        cmd.runCommand(handle, {}, ['rbuild', 'delete', 'images', '10', '11'])
        handle.Images.delete._mock.assertCalled('10', False)
        handle.Images.delete._mock.assertCalled('11', False)

        cmd.runCommand(handle, {"force": True},
                       ['rbuild', 'delete', 'images', '10'])
        handle.Images.delete._mock.assertCalled('10', True)

        cmd.runCommand(handle, {},
            ['rbuild', 'delete', 'images', '&^%&*%$^&$'])
        handle.Images.delete._mock.assertNotCalled()
        handle.ui.warning._mock.assertCalled(
            "Cannot parse image id '&^%&*%$^&$'")

    def testCommand(self):
        self.checkRbuild('delete images',
            'rbuild_plugins.images.DeleteImagesCommand.runCommand',
            [None, None, {}, ['delete', 'images']])
        self.checkRbuild('delete images 1 2',
            'rbuild_plugins.images.DeleteImagesCommand.runCommand',
            [None, None, {}, ['delete', 'images', '1', '2']])
        self.checkRbuild('delete images --force 1 2',
            'rbuild_plugins.images.DeleteImagesCommand.runCommand',
            [None, None, {"force": True}, ['delete', 'images', '1', '2']])


class LaunchTest(AbstractImagesTest):
    def testLaunchArgParse(self):
        self.checkRbuild(
            'launch --list --from-file=fromFile --to-file=toFile --no-launch'
                ' --no-watch Image Target',
            'rbuild_plugins.images.LaunchCommand.runCommand',
            [None, None, {
                'list': True,
                'from-file': 'fromFile',
                'to-file': 'toFile',
                'no-watch': True,
                'no-launch': True,

                }, ['rbuild', 'launch', 'Image', 'Target']])
        self.checkRbuild(
            'deploy --list --from-file=fromFile --to-file=toFile --no-launch'
                ' --no-watch Image Target',
            'rbuild_plugins.images.LaunchCommand.runCommand',
            [None, None, {
                'list': True,
                'from-file': 'fromFile',
                'to-file': 'toFile',
                'no-watch': True,
                'no-launch': True,
                }, ['rbuild', 'deploy', 'Image', 'Target']])

    def testLaunchCmdlineList(self):
        handle = self.handle
        handle.Images.registerCommands()
        handle.Images.initialize()
        handle.ui = mock.MockObject()

        _target_1 = mock.MockObject()
        _target_1._mock.set(name='foo')

        _target_2 = mock.MockObject()
        _target_2._mock.set(name='bar')

        _targets = [_target_1, _target_2]
        mock.mockMethod(handle.facade.rbuilder.getEnabledTargets, _targets)

        cmd = handle.Commands.getCommandClass('launch')()
        cmd.runCommand(handle, {'list': True}, ['rbuild', 'launch'])

        handle.ui.write._mock.assertCalled('Available targets: foo, bar')

    def testLaunchCmdlineNoArgs(self):
        handle = self.handle

        cmd = handle.Commands.getCommandClass('launch')()

        self.assertRaises(
            errors.ParseError,
            cmd.runCommand,
            handle,
            {},
            ['rbuild', 'launch'],
            )
        self.assertRaises(
            errors.ParseError,
            cmd.runCommand,
            handle,
            {},
            ['rbuild', 'launch', 'foo'],
            )

    def testLaunchCmdline(self):
        handle = self.handle
        mock.mockMethod(handle.Images.deployImage)
        mock.mockMethod(handle.Images.launchImage)
        mock.mockMethod(handle.Images.watchJob)

        cmd = handle.Commands.getCommandClass('launch')()
        cmd.runCommand(handle, {}, ['rbuild', 'launch', 'foo', 'bar'])
        handle.Images.deployImage._mock.assertNotCalled()
        handle.Images.launchImage._mock.assertCalled('foo', 'bar', True)

        cmd = handle.Commands.getCommandClass('launch')()
        cmd.runCommand(
            handle, {}, ['rbuild', 'deploy', 'foo', 'bar'])
        handle.Images.deployImage._mock.assertCalled('foo', 'bar', True)
        handle.Images.launchImage._mock.assertNotCalled()


class ListImagesTest(AbstractImagesTest):
    def testCommand(self):
        self.getRbuildHandle()
        self.checkRbuild('list images',
            'rbuild_plugins.images.ListImagesCommand.runCommand',
            [None, None, {}, ['list', 'images']])
        self.checkRbuild('list images 1 2',
            'rbuild_plugins.images.ListImagesCommand.runCommand',
            [None, None, {}, ['list', 'images', '1', '2']])

    def testLatestImages(self):
        '''Regression test for APPENG-2788'''
        from rbuild.pluginapi import command
        handle = self.handle
        handle.List.registerCommands()
        handle.Delete.registerCommands()
        handle.Images.initialize()

        mock.mock(handle, 'ui')

        _latest = mock.MockObject()
        _latest._mock.set(id='http://localhost/latest')
        _resource = mock.MockObject()
        _resource._node._mock.set(latest_files=[_latest])
        mock.mock(command.ListCommand, '_list', _resource)

        cmd = handle.Commands.getCommandClass('list')()
        cmd.runCommand(handle, {}, ['rbuild', 'list', 'images'])
        handle.ui.write._mock.assertCalled('http://localhost/latest')

        _latest._mock.set(id='http://localhost/latest%20image')
        cmd.runCommand(handle, {}, ['rbuild', 'list', 'images'])
        handle.ui.write._mock.assertCalled(
            'http://localhost/latest%%20image')


class ShowImagesTest(AbstractImagesTest):
    def testCommand(self):
        self.getRbuildHandle()
        self.checkRbuild('show images',
            'rbuild_plugins.images.ListImagesCommand.runCommand',
            [None, None, {}, ['show', 'images']])
        self.checkRbuild('show images 1 2',
            'rbuild_plugins.images.ListImagesCommand.runCommand',
            [None, None, {}, ['show', 'images', '1', '2']])


class ImagesPluginTest(AbstractImagesTest):
    def testCancel(self):
        from rbuild_plugins import images

        mock.mockMethod(self.handle.DescriptorConfig.createDescriptorData)
        mock.mock(images, 'xobj')

        _doc = mock.MockObject()
        _doc._mock.enable('job')
        images.xobj.Document._mock.setReturn(_doc)

        _job = mock.MockObject()
        _job._mock.enable('job_type', 'descriptor')
        images.xobj.XObj._mock.setReturn(_job)

        _image_action = mock.MockObject()
        _image_action._mock.set(key=images.Images.CANCEL)
        _image_action._root._mock.set(job_type='job_type',
            descriptor='descriptor')

        _image = mock.MockObject()
        _image._mock.set(key=images.Images.CANCEL, image_id='10', status='100',
            actions=[_image_action])
        _image.jobs.append._mock.setReturn(_doc, _doc)

        rv = self.handle.Images.cancel(_image)
        self.assertEqual(rv, _doc)
        self.assertEqual(rv.job, _job)
        self.assertEqual('job_type', rv.job.job_type)
        self.assertEqual('descriptor', rv.job.descriptor)

    def testCancelNonBuilding(self):
        from rbuild_plugins import images

        _image = mock.MockObject()
        _image._mock.set(status='300')
        err = self.assertRaises(images.CancelImageError,
            self.handle.Images.cancel, _image)
        self.assertIn('not currently building', str(err))

    def testCancelNoCancelAction(self):
        from rbuild_plugins import images

        _image = mock.MockObject()
        _image._mock.set(status='100')
        err = self.assertRaises(images.CancelImageError,
            self.handle.Images.cancel, _image)
        self.assertIn('cancel action', str(err))

    def testCreateJob(self):
        handle = self.handle

        mock.mockMethod(
            handle.Images._getProductStage, ('product', 'branch', 'stage'))

        _jobs = []

        def _append(x):
            _jobs.append(x)
            return x

        _image = mock.MockObject()
        _image._mock.set(jobs=mock.MockObject())
        _image.jobs._mock.set(append=_append)
        mock.mockMethod(handle.facade.rbuilder.getImages, _image)

        _target = mock.MockObject()
        _target._mock.set(credentials_valid='false', is_configured='false')

        # test no matching target
        mock.mockMethod(handle.facade.rbuilder.getTargets, [])
        err = self.assertRaises(errors.PluginError,
            handle.Images._createJob, handle.Images.LAUNCH, 'foo', 'bar', True)
        self.assertIn('No target matching', str(err))

        # test unconfigured target
        handle.facade.rbuilder.getTargets._mock.setDefaultReturn([_target])
        err = self.assertRaises(errors.PluginError,
            handle.Images._createJob, handle.Images.LAUNCH, 'foo', 'bar', True)
        self.assertIn('is not configured', str(err))

        # test no credentials
        _target._mock.set(is_configured='true')
        err = self.assertRaises(errors.PluginError,
            handle.Images._createJob, handle.Images.LAUNCH, 'foo', 'bar', True)
        self.assertIn('have valid credentials', str(err))

        _target._mock.set(credentials_valid='true')

        _action = mock.MockObject()
        _action._mock.set(descriptor=DESCRIPTOR_XML)
        _action._root._mock.set(job_type='job_type')
        _action._root._mock.set(descriptor='descriptor')
        mock.mockMethod(handle.Images._getAction, (_image, _action))

        _ddata = mock.MockObject()
        _ddata.toxml._mock.setDefaultReturn(DDATA_XML)
        mock.mockMethod(handle.DescriptorConfig.createDescriptorData, _ddata)

        rv = handle.Images._createJob(
            handle.Images.DEPLOY, 'foo', 'bar', True)
        handle.facade.rbuilder.getImages._mock.assertCalled(
            name='foo',
            project='product',
            branch='branch',
            stage='stage',
            order_by='-time_created',
            )
        handle.Images._getAction._mock.assertCalled(
            _image, _target, handle.Images.DEPLOY)

        self.assertEqual(len(_jobs), 1)
        self.assertEqual(rv, _jobs[0])
        self.assertEqual(rv.toxml(), JOB_XML)

        rv = handle.Images._createJob(
            handle.Images.DEPLOY, 'foo=', 'bar', True)
        handle.facade.rbuilder.getImages._mock.assertCalled(
            name='foo',
            project='product',
            branch='branch',
            stage='stage',
            order_by='-time_created',
            )
        handle.Images._getAction._mock.assertCalled(
            _image, _target, handle.Images.DEPLOY)

        self.assertEqual(len(_jobs), 2)
        self.assertEqual(rv, _jobs[1])
        self.assertEqual(rv.toxml(), JOB_XML)

        rv = handle.Images._createJob(
            handle.Images.DEPLOY, 'foo=1', 'bar', True)
        handle.facade.rbuilder.getImages._mock.assertCalled(
            name='foo',
            project='product',
            branch='branch',
            stage='stage',
            order_by='-time_created',
            trailing_version='1',
            )
        handle.Images._getAction._mock.assertCalled(
            _image, _target, handle.Images.DEPLOY)

        self.assertEqual(len(_jobs), 3)
        self.assertEqual(rv, _jobs[2])
        self.assertEqual(rv.toxml(), JOB_XML)

        rv = handle.Images._createJob(
            handle.Images.DEPLOY, '1', 'bar', True)
        handle.facade.rbuilder.getImages._mock.assertCalled(
            image_id='1',
            project='product',
            branch='branch',
            stage='stage',
            order_by='-time_created',
            )
        handle.Images._getAction._mock.assertCalled(
            _image, _target, handle.Images.DEPLOY)

        self.assertEqual(len(_jobs), 4)
        self.assertEqual(rv, _jobs[3])
        self.assertEqual(rv.toxml(), JOB_XML)

    def testCreateJobNoImages(self):
        '''Regression test for APPENG-2803'''
        handle = self.handle
        handle.Images.registerCommands()
        handle.Images.initialize()

        mock.mockMethod(
            handle.Images._getProductStage, ('product', 'branch', 'stage'))
        mock.mockMethod(handle.facade.rbuilder.getImages, None)

        err = self.assertRaises(
            errors.PluginError,
            handle.Images._createJob,
            handle.Images.DEPLOY,
            'none',
            'bar',
            True,
            )
        self.assertIn('image matching', str(err))

    def testDelete(self):
        handle = self.handle

        _image = mock.MockObject(name="foo")
        mock.mockMethod(handle.facade.rbuilder.getImages)
        handle.facade.rbuilder.getImages._mock.setReturn(
            [_image], image_id=10, project="project", branch="branch",
            stage="stage")

        mock.mockMethod(handle.Images._getProductStage,
            ('project', 'branch', 'stage'))

        mock.mockMethod(handle.ui.getYn, False)
        handle.ui.getYn._mock.appendReturn(True, "Delete foo?", default=False)

        handle.Images.delete(10, force=True)
        handle.ui.getYn._mock.assertNotCalled()
        handle.facade.rbuilder.getImages._mock.assertCalled(
            image_id=10, project='project', branch='branch', stage='stage')
        _image.delete._mock.assertCalled()

        handle.Images.delete(10)
        handle.facade.rbuilder.getImages._mock.assertCalled(
            image_id=10, project='project', branch='branch', stage='stage')
        _image.delete._mock.assertCalled()


    def testDeleteMissing(self):
        from rbuild_plugins import images

        handle = self.handle

        mock.mockMethod(handle.facade.rbuilder.getImages, None)
        mock.mockMethod(handle.Images._getProductStage,
            ('project', 'branch', 'stage'))

        self.assertRaises(images.MissingImageError, handle.Images.delete, 10)
        handle.facade.rbuilder.getImages._mock.assertCalled(
            image_id=10, project='project', branch='branch', stage='stage')

    def testDeleteNoProduct(self):
        handle = self.handle

        mock.mockMethod(handle.facade.rbuilder.getImages)
        mock.mockMethod(handle.Images._getProductStage)
        handle.Images._getProductStage._mock.raiseErrorOnAccess(
            errors.MissingProductStoreError(path='/foo'))

        self.assertRaises(errors.MissingProductStoreError,
            handle.Images.delete, 10)
        handle.facade.rbuilder.getImages._mock.assertNotCalled()

    def testDeleteNoStage(self):
        handle = self.handle

        mock.mockMethod(handle.facade.rbuilder.getImages)
        mock.mockMethod(handle.Images._getProductStage)
        handle.Images._getProductStage._mock.raiseErrorOnAccess(
            errors.MissingActiveStageError(path='/foo'))

        self.assertRaises(errors.MissingActiveStageError,
            handle.Images.delete, 10)
        handle.facade.rbuilder.getImages._mock.assertNotCalled()

    def testGetAction(self):
        handle = self.handle
        handle.Images.registerCommands()
        handle.Images.initialize()

        self.assertRaises(
            AssertionError, handle.Images._getAction, None, None, 'foo')

        _action1 = mock.MockObject()
        _action1._mock.set(key=handle.Images.DEPLOY)
        _action1._mock.set(name="Deploy image on 'foo' (vmware)")
        _action2 = mock.MockObject()
        _action2._mock.set(key=handle.Images.DEPLOY)
        _action2._mock.set(name="Deploy image on 'bar' (vmware)")

        _image = mock.MockObject()
        _image._mock.set(actions=[_action1, _action2])

        _target = mock.MockObject()
        _target._mock.set(name='foo')

        self.assertRaises(
            errors.PluginError,
            handle.Images._getAction,
            [_image],
            _target,
            handle.Images.DEPLOY,
            )

        _target._mock.set(name='baz')
        _image._mock.set(status='300')
        self.assertRaises(
            errors.PluginError,
            handle.Images._getAction,
            [_image],
            _target,
            handle.Images.DEPLOY,
            )

        _target._mock.set(name='foo')
        rv = handle.Images._getAction([_image], _target, handle.Images.DEPLOY)
        self.assertEqual(rv, (_image, _action1))

        _target._mock.set(name='bar')
        rv = handle.Images._getAction([_image], _target, handle.Images.DEPLOY)
        self.assertEqual(rv, (_image, _action2))

    def testList(self):
        handle = self.handle

        mock.mockMethod(handle.facade.rbuilder.getImages)
        mock.mockMethod(handle.Images._getProductStage)
        handle.Images._getProductStage._mock.setReturn(
            ('project', 'branch', 'stage'))

        handle.Images.list()
        handle.facade.rbuilder.getImages._mock.assertCalled(
            project='project', branch='branch', stage='stage')

    def testListNoProduct(self):
        handle = self.handle

        mock.mockMethod(handle.facade.rbuilder.getImages)
        mock.mockMethod(handle.Images._getProductStage)
        handle.Images._getProductStage._mock.raiseErrorOnAccess(
            errors.MissingProductStoreError(path='/foo'))

        self.assertRaises(errors.MissingProductStoreError, handle.Images.list)
        handle.facade.rbuilder.getImages._mock.assertNotCalled()

    def testListNoStage(self):
        handle = self.handle

        mock.mockMethod(handle.facade.rbuilder.getImages)
        mock.mockMethod(handle.Images._getProductStage)
        handle.Images._getProductStage._mock.raiseErrorOnAccess(
            errors.MissingActiveStageError(path='/foo'))

        self.assertRaises(errors.MissingActiveStageError,
            handle.Images.list)
        handle.facade.rbuilder.getImages._mock.assertNotCalled()

    def testShow(self):
        handle = self.handle

        mock.mock(handle, 'productStore')
        mock.mock(handle, 'product')
        handle.product.getProductShortname._mock.setReturn('project')
        handle.productStore.getActiveStageName._mock.setReturn('stage')
        handle.product.getBaseLabel._mock.setReturn('branch')
        mock.mockMethod(handle.facade.rbuilder.getImages, ['image'])

        rv = handle.Images.show(10)
        self.assertEqual(rv, 'image')
        handle.facade.rbuilder.getImages._mock.assertCalled(
            image_id=10, project='project', branch='branch', stage='stage')

    def testShowMissing(self):
        handle = self.handle

        mock.mock(handle, 'productStore')
        mock.mock(handle, 'product')
        mock.mock(handle, 'ui')
        handle.product.getProductShortname._mock.setReturn('project')
        handle.product.getBaseLabel._mock.setReturn('branch')
        handle.productStore.getActiveStageName._mock.setReturn('stage')
        mock.mockMethod(handle.facade.rbuilder.getImages, None)

        handle.Images.show(10)
        handle.facade.rbuilder.getImages._mock.assertCalled(
            image_id=10, project='project', branch='branch', stage='stage')

    def testShowNoProduct(self):
        handle = self.handle

        mock.mockMethod(handle.facade.rbuilder.getImages)
        mock.mockMethod(handle.Images._getProductStage)
        handle.Images._getProductStage._mock.raiseErrorOnAccess(
            errors.MissingProductStoreError(path='/foo'))

        self.assertRaises(errors.MissingProductStoreError,
            handle.Images.delete, 10)
        handle.facade.rbuilder.getImages._mock.assertNotCalled()

    def testShowNoStage(self):
        handle = self.handle

        mock.mockMethod(handle.facade.rbuilder.getImages)
        mock.mockMethod(handle.Images._getProductStage)
        handle.Images._getProductStage._mock.raiseErrorOnAccess(
            errors.MissingActiveStageError(path='/foo'))

        self.assertRaises(errors.MissingActiveStageError,
            handle.Images.show, 10)
        handle.facade.rbuilder.getImages._mock.assertNotCalled()

    def testWatchJob(self):
        from rbuild_plugins.images import time
        handle = self.handle

        mock.mock(handle.ui, 'outStream')

        mock.mock(time, 'ctime', '')
        mock.mock(time, 'sleep')

        _job = mock.MockObject()
        _job.job_state._mock.set(name='Failed')
        _job.job_type._mock.set(name='launch system on taraget')

        self.assertRaises(errors.PluginError, handle.Images.watchJob, _job)

        _status_text = ['Text4', 'Text3 ', 'Text2  ', 'Text1   ']
        _network1 = mock.MockObject()
        _network1._mock.set(dns_name='foo')
        _network2 = mock.MockObject()
        _network2._mock.set(dns_name='bar')
        _resource = mock.MockObject()
        _resource._mock.set(name='baz')
        _resource._mock.set(networks=[_network1, _network2])

        def _refresh():
            try:
                _job._mock.set(status_text=_status_text.pop())
            except IndexError:
                _job.job_state._mock.set(name='Completed')
                _job._mock.set(created_resources=[_resource])

        _job._mock.set(refresh=_refresh)
        _job.job_state._mock.set(name='Running')
        _job._mock.set(status_text='Text0    ')

        handle.ui.outStream.isatty._mock.setDefaultReturn(True)
        handle.Images.watchJob(_job)
        expected_calls = [
            (('\r[] Text0    ',), ()),
            (('\r[] Text1   ',), ()),
            (('  \b\b',), ()),
            (('\r[] Text2  ',), ()),
            (('  \b\b',), ()),
            (('\r[] Text3 ',), ()),
            (('  \b\b',), ()),
            (('\r[] Text4',), ()),
            (('  \b\b',), ()),
            (('\n',), ()),
            (('Created system baz with addresses: foo, bar\n',), ()),
            ]
        self.assertEqual(handle.ui.outStream.write._mock.calls, expected_calls)

        _status_text = ['Text4', 'Text3 ', 'Text2  ', 'Text1   ']
        _job.job_state._mock.set(name='Running')
        _job._mock.set(status_text='Text0    ')
        handle.ui.outStream.write._mock.calls = []
        handle.ui.outStream.isatty._mock.setDefaultReturn(False)
        handle.Images.watchJob(_job)
        expected_calls = [
            (('[] Text0    \n',), ()),
            (('[] Text1   \n',), ()),
            (('[] Text2  \n',), ()),
            (('[] Text3 \n',), ()),
            (('[] Text4\n',), ()),
            (('Created system baz with addresses: foo, bar\n',), ()),
            ]
        self.assertEqual(handle.ui.outStream.write._mock.calls, expected_calls)
