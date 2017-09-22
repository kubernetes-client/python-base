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

# Reference https://github.com/kubernetes/kubernetes/blob/5c558ddb185a7c120e147f24d69b7470bf7457e2/pkg/kubectl/cmd/drain.go # noqa

from kubernetes import client

KUBE_NAMESPACE = 'kube-system'


class Drainer(object):

    def __init__(self, node_name, api=None):
        """Initialize drainer object for given node name."""
        self._node_name = node_name
        self._api = api if api is not None else client.CoreV1Api()

    def _get_user_pods_for_node(self):
        """Returns list of user pods."""
        response = self._api.list_pod_for_all_namespaces()
        # filter pods by node name and
        # filter out all pods in kubernetes namespace.
        # we only want to return user pods.
        pods = [p for p in response.items
                if (p.metadata.namespace != KUBE_NAMESPACE and
                    p.spec.node_name == self._node_name)]
        return pods

    def _set_unschedulable(self, unschedulable):
        """set unschedulable attribute for current node."""
        body = {
            "spec": {
                'unschedulable': unschedulable
            }
        }

        response = self._api.patch_node(self._node_name, body)
        return response

    def _delete_pod(self, pod, delete_options=None):
        """Delete given pod."""
        name = pod.metadata.name
        namespace = pod.metadata.namespace
        if delete_options is None:
            delete_options = client.V1DeleteOptions()
        return self._api.delete_namespaced_pod(name, namespace, delete_options)

    def cordon(self):
        """Cordon current node."""
        return self._set_unschedulable(True)

    def uncordon(self):
        """Uncordon current node."""
        return self._set_unschedulable(False)

    def drain(self, delete_options=None):
        """Drain current node."""
        self.cordon()
        pods = self._get_user_pods_for_node()
        response = []
        for pod in pods:
            response.append(self._delete_pod(pod))
        return response
