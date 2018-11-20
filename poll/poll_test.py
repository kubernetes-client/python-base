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

import sys
import time
import unittest

from .poll import Poll


class PollTest(unittest.TestCase):

    def test_poll_client(self):
        p = Poll(sys.stderr)
        start = time.time()
        r = p.read_until(1)
        end = time.time()
        self.assertTrue((end-start) < 2)
        self.assertFalse(p.closed)


if __name__ == '__main__':
    unittest.main()
