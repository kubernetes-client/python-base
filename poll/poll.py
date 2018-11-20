# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import select


class Poll(object):
    """Add non-blocking interface to an object which only has blocking io.
    Example:
        v1 = kubernetes.client.CoreV1Api()
        log_stream = poll.Poll(v1.read_namespaced_pod_log(
            name="hello", namespace="default",
            _preload_content=False, follow=True,
            tail_lines=200
        ))
        while True:
            if client_close or log_steam.isclosed():
                break
            c = log_stream.read_until(timeout=0)
            # process the log
            time.sleep(.1)
        log_stream.close()
    """

    def __init__(self, io_obj):
        self._poll = select.poll()
        self._poll.register(io_obj.fileno())
        self._io = io_obj

    def read_until(self, timeout=0):
        content = bytearray()
        _, code = self._poll.poll(timeout)[0]
        while True:
            if not (code & select.POLLIN):
                break
            content.extend(self._io.read(1))
            _, code = self._poll.poll(0)[0]
        return content.decode()

    def __getattr__(self, attr):
         if attr in self.__dict__:
             return getattr(self, attr)
         return getattr(self._io, attr)

