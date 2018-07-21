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

from . import ws_client


def stream(func, *args, **kwargs):
    """Stream given API call using websocket"""

    def _intercept_request_call(*args, **kwargs):
        # old generated code's api client has config. new ones has
        # configuration
        try:
            config = func.__self__.api_client.configuration
        except AttributeError:
            config = func.__self__.api_client.config

        return ws_client.websocket_call(config, *args, **kwargs)

    def _intercept_deserialize_call(response, response_type):
        return response.data

    prev_request = func.__self__.api_client.request
    prev_deserialize = func.__self__.api_client.deserialize
    try:
        func.__self__.api_client.request = _intercept_request_call
        func.__self__.api_client.deserialize = _intercept_deserialize_call
        return func(*args, **kwargs)
    finally:
        func.__self__.api_client.request = prev_request
        func.__self__.api_client.deserialize = prev_deserialize
