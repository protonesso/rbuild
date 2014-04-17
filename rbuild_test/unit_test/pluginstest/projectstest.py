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


from testutils import mock

from rbuild_test import rbuildhelp


class ListProjectsTest(rbuildhelp.RbuildHelper):
    def testCommandParsing(self):
        handle = self.getRbuildHandle()
        handle.List.registerCommands()
        handle.List.initialize()
        handle.Projects.initialize()
        cmd = handle.Commands.getCommandClass('list')()

        mock.mockMethod(handle.Projects.list)

        cmd.runCommand(handle, {}, ['rbuild', 'list', 'projects'])
        handle.Projects.list._mock.assertCalled()

    def testCommand(self):
        self.getRbuildHandle()
        self.checkRbuild(
            'list projects',
            'rbuild_plugins.projects.ListProjectsCommand.runCommand',
            [None, None, {}, ['list', 'projects']],
            )


class ProjectsPluginTest(rbuildhelp.RbuildHelper):
    def testList(self):
        handle = self.getRbuildHandle()

        mock.mockMethod(handle.facade.rbuilder.getProjects)

        _project1 = mock.MockObject()
        _project2 = mock.MockObject()
        _project3 = mock.MockObject()

        handle.facade.rbuilder.getProjects._mock.setReturn(
            [_project1], disabled='false', hidden='false')
        handle.facade.rbuilder.getProjects._mock.setReturn(
            [_project2], disabled='true', hidden='false')
        handle.facade.rbuilder.getProjects._mock.setReturn(
            [_project3], disabled='false', hidden='true')
        handle.facade.rbuilder.getProjects._mock.setReturn(
            [_project1, _project2], disabled='true', hidden='true')

        rv = handle.Projects.list()
        self.assertEqual(rv, [_project1])

        rv = handle.Projects.list(disabled='false')
        self.assertEqual(rv, [_project1])

        rv = handle.Projects.list(hidden='false')
        self.assertEqual(rv, [_project1])

        rv = handle.Projects.list(disabled='false', hidden='false')
        self.assertEqual(rv, [_project1])

        rv = handle.Projects.list(disabled='true')
        self.assertEqual(rv, [_project2])

        rv = handle.Projects.list(disabled='true', hidden='false')
        self.assertEqual(rv, [_project2])

        rv = handle.Projects.list(hidden='true')
        self.assertEqual(rv, [_project3])

        rv = handle.Projects.list(hidden='true', disabled='false')
        self.assertEqual(rv, [_project3])

        rv = handle.Projects.list(hidden='true', disabled='true')
        self.assertEqual(rv, [_project1, _project2])