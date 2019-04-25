#!/usr/bin/env python

# Copyright 2016 The Kubernetes Authors.
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

import unittest

from mock import Mock, call

from .watch import Watch


class WatchTests(unittest.TestCase):
    def setUp(self):
        # counter for a test that needs test global state
        self.callcount = 0

    def test_watch_with_decode(self):
        fake_resp = Mock()
        fake_resp.close = Mock()
        fake_resp.release_conn = Mock()
        fake_resp.read_chunked = Mock(
            return_value=[
                '{"type": "ADDED", "object": {"metadata": {"name": "test1",'
                '"resourceVersion": "1"}, "spec": {}, "status": {}}}\n',
                '{"type": "ADDED", "object": {"metadata": {"name": "test2",'
                '"resourceVersion": "2"}, "spec": {}, "sta',
                'tus": {}}}\n'
                '{"type": "ADDED", "object": {"metadata": {"name": "test3",'
                '"resourceVersion": "3"}, "spec": {}, "status": {}}}\n',
                'should_not_happened\n'])

        fake_api = Mock()
        fake_api.get_namespaces = Mock(return_value=fake_resp)
        fake_api.get_namespaces.__doc__ = ':return: V1NamespaceList'

        w = Watch()
        count = 1
        for e in w.stream(fake_api.get_namespaces):
            self.assertEqual("ADDED", e['type'])
            # make sure decoder worked and we got a model with the right name
            self.assertEqual("test%d" % count, e['object'].metadata.name)
            # make sure decoder worked and updated Watch.resource_version
            self.assertEqual(
                "%d" % count, e['object'].metadata.resource_version)
            self.assertEqual("%d" % count, w.resource_version)
            count += 1
            # make sure we can stop the watch and the last event with won't be
            # returned
            if count == 4:
                w.stop()

        fake_api.get_namespaces.assert_called_once_with(
            _preload_content=False, watch=True)
        fake_resp.read_chunked.assert_called_once_with(decode_content=False)
        fake_resp.close.assert_called_once()
        fake_resp.release_conn.assert_called_once()

    def test_watch_for_follow(self):
        fake_resp = Mock()
        fake_resp.close = Mock()
        fake_resp.release_conn = Mock()
        fake_resp.read_chunked = Mock(
            return_value=[
                'log_line_1\n',
                'log_line_2\n'])

        fake_api = Mock()
        fake_api.read_namespaced_pod_log = Mock(return_value=fake_resp)
        fake_api.read_namespaced_pod_log.__doc__ = ':param bool follow:\n:return: str'

        w = Watch()
        count = 1
        for e in w.stream(fake_api.read_namespaced_pod_log):
            self.assertEqual("log_line_1", e)
            count += 1
            # make sure we can stop the watch and the last event with won't be
            # returned
            if count == 2:
                w.stop()

        fake_api.read_namespaced_pod_log.assert_called_once_with(
            _preload_content=False, follow=True)
        fake_resp.read_chunked.assert_called_once_with(decode_content=False)
        fake_resp.close.assert_called_once()
        fake_resp.release_conn.assert_called_once()

    def test_watch_resource_version_set(self):
        # https://github.com/kubernetes-client/python/issues/700
        # ensure watching from a resource version does reset to resource
        # version 0 after k8s resets the watch connection
        fake_resp = Mock()
        fake_resp.close = Mock()
        fake_resp.release_conn = Mock()
        values = [
            '{"type": "ADDED", "object": {"metadata": {"name": "test1",'
            '"resourceVersion": "1"}, "spec": {}, "status": {}}}\n',
            '{"type": "ADDED", "object": {"metadata": {"name": "test2",'
            '"resourceVersion": "2"}, "spec": {}, "sta',
            'tus": {}}}\n'
            '{"type": "ADDED", "object": {"metadata": {"name": "test3",'
            '"resourceVersion": "3"}, "spec": {}, "status": {}}}\n'
        ]
        # return nothing on the first call and values on the second
        # this emulates a watch from a rv that returns nothing in the first k8s
        # watch reset and values later

        def get_values(*args, **kwargs):
            self.callcount += 1
            if self.callcount == 1:
                return []
            else:
                return values

        fake_resp.read_chunked = Mock(
            side_effect=get_values)

        fake_api = Mock()
        fake_api.get_namespaces = Mock(return_value=fake_resp)
        fake_api.get_namespaces.__doc__ = ':return: V1NamespaceList'

        w = Watch()
        # ensure we keep our requested resource version or the version latest
        # returned version when the existing versions are older than the
        # requested version
        # needed for the list existing objects, then watch from there use case
        calls = []

        iterations = 2
        # first two calls must use the passed rv, the first call is a
        # "reset" and does not actually return anything
        # the second call must use the same rv but will return values
        # (with a wrong rv but a real cluster would behave correctly)
        # calls following that will use the rv from those returned values
        calls.append(call(_preload_content=False, watch=True,
                          resource_version="5"))
        calls.append(call(_preload_content=False, watch=True,
                          resource_version="5"))
        for i in range(iterations):
            # ideally we want 5 here but as rv must be treated as an
            # opaque value we cannot interpret it and order it so rely
            # on k8s returning the events completely and in order
            calls.append(call(_preload_content=False, watch=True,
                              resource_version="5"))

        for c, e in enumerate(w.stream(fake_api.get_namespaces,
                                       resource_version="5")):
            if c == len(values) * iterations:
                w.stop()

        # check calls are in the list, gives good error output
        fake_api.get_namespaces.assert_has_calls(calls)
        # more strict test with worse error message
        self.assertEqual(fake_api.get_namespaces.mock_calls, calls)

    def test_watch_resource_version_grows_monotonically(self):
        # https://github.com/kubernetes-client/python/issues/700
        # ensure that the resource version never decrements,
        # especially on the first listing of the resources
        # (as they go in arbitrary order, not sorted).
        fake_resp = Mock()
        fake_resp.close = Mock()
        fake_resp.release_conn = Mock()
        fake_resp.read_chunked = Mock(
            return_value=[
                '{"type": "ADDED", "object": {"metadata": {"name": "test1",'
                '"resourceVersion": "1"}, "spec": {}, "status": {}}}\n',
                '{"type": "ADDED", "object": {"metadata": {"name": "test2",'
                '"resourceVersion": "3"}, "spec": {}, "status": {}}}\n'
                '{"type": "ADDED", "object": {"metadata": {"name": "test3",'
                '"resourceVersion": "2"}, "spec": {}, "status": {}}}\n',
                'should_not_happened\n'])

        fake_api = Mock()
        fake_api.get_namespaces = Mock(return_value=fake_resp)
        fake_api.get_namespaces.__doc__ = ':return: V1NamespaceList'

        w = Watch()
        watch_resource_versions = []
        event_resource_versions = []
        count = 1
        for e in w.stream(fake_api.get_namespaces):
            obj = e['object']
            watch_resource_versions.append(w.resource_version)
            event_resource_versions.append(obj.metadata.resource_version)
            count += 1
            if count == 4:
                w.stop()

        self.assertEqual(watch_resource_versions, ['1', '3', '3'])
        self.assertEqual(event_resource_versions, ['1', '3', '2'])

    def test_watch_stream_twice(self):
        w = Watch(float)
        for step in ['first', 'second']:
            fake_resp = Mock()
            fake_resp.close = Mock()
            fake_resp.release_conn = Mock()
            fake_resp.read_chunked = Mock(
                return_value=['{"type": "ADDED", "object": 1}\n'] * 4)

            fake_api = Mock()
            fake_api.get_namespaces = Mock(return_value=fake_resp)
            fake_api.get_namespaces.__doc__ = ':return: V1NamespaceList'

            count = 1
            for e in w.stream(fake_api.get_namespaces):
                count += 1
                if count == 3:
                    w.stop()

            self.assertEqual(count, 3)
            fake_api.get_namespaces.assert_called_once_with(
                _preload_content=False, watch=True)
            fake_resp.read_chunked.assert_called_once_with(
                decode_content=False)
            fake_resp.close.assert_called_once()
            fake_resp.release_conn.assert_called_once()

    def test_watch_stream_loop(self):
        w = Watch(float)

        fake_resp = Mock()
        fake_resp.close = Mock()
        fake_resp.release_conn = Mock()
        fake_resp.read_chunked = Mock(
            return_value=['{"type": "ADDED", "object": 1}\n'])

        fake_api = Mock()
        fake_api.get_namespaces = Mock(return_value=fake_resp)
        fake_api.get_namespaces.__doc__ = ':return: V1NamespaceList'

        count = 0

        # when timeout_seconds is set, auto-exist when timeout reaches
        for e in w.stream(fake_api.get_namespaces, timeout_seconds=1):
            count = count + 1
        self.assertEqual(count, 1)

        # when no timeout_seconds, only exist when w.stop() is called
        for e in w.stream(fake_api.get_namespaces):
            count = count + 1
            if count == 2:
                w.stop()

        self.assertEqual(count, 2)
        self.assertEqual(fake_api.get_namespaces.call_count, 2)
        self.assertEqual(fake_resp.read_chunked.call_count, 2)
        self.assertEqual(fake_resp.close.call_count, 2)
        self.assertEqual(fake_resp.release_conn.call_count, 2)

    def test_unmarshal_with_float_object(self):
        w = Watch()
        event = w.unmarshal_event('{"type": "ADDED", "object": 1}', 'float')
        self.assertEqual("ADDED", event['type'])
        self.assertEqual(1.0, event['object'])
        self.assertTrue(isinstance(event['object'], float))
        self.assertEqual(1, event['raw_object'])

    def test_unmarshal_with_no_return_type(self):
        w = Watch()
        event = w.unmarshal_event('{"type": "ADDED", "object": ["test1"]}',
                                  None)
        self.assertEqual("ADDED", event['type'])
        self.assertEqual(["test1"], event['object'])
        self.assertEqual(["test1"], event['raw_object'])

    def test_unmarshal_with_custom_object(self):
        w = Watch()
        event = w.unmarshal_event('{"type": "ADDED", "object": {"apiVersion":'
                                  '"test.com/v1beta1","kind":"foo","metadata":'
                                  '{"name": "bar", "resourceVersion": "1"}}}',
                                  'object')
        self.assertEqual("ADDED", event['type'])
        # make sure decoder deserialized json into dictionary and updated
        # Watch.resource_version
        self.assertTrue(isinstance(event['object'], dict))
        self.assertEqual("1", event['object']['metadata']['resourceVersion'])
        self.assertEqual("1", w.resource_version)

    def test_watch_with_exception(self):
        fake_resp = Mock()
        fake_resp.close = Mock()
        fake_resp.release_conn = Mock()
        fake_resp.read_chunked = Mock(side_effect=KeyError('expected'))

        fake_api = Mock()
        fake_api.get_thing = Mock(return_value=fake_resp)

        w = Watch()
        try:
            for _ in w.stream(fake_api.get_thing):
                self.fail(self, "Should fail on exception.")
        except KeyError:
            pass
            # expected

        fake_api.get_thing.assert_called_once_with(
            _preload_content=False, watch=True)
        fake_resp.read_chunked.assert_called_once_with(decode_content=False)
        fake_resp.close.assert_called_once()
        fake_resp.release_conn.assert_called_once()


if __name__ == '__main__':
    unittest.main()
