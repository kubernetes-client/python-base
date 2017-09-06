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

from kubernetes import client, config

KUBE_NAMESPACE = 'kube-system'


class Drainer(object):

    def __init__(self, node_name, api=None):
        config.load_kube_config()
        self._node_name = node_name
        self._api = api if api is not None else client.CoreV1Api()

    def _get_user_pods_for_node(self):
        response = self._api.list_pod_for_all_namespaces()
        # filter pods by node name.
        pods = [p for p in response.items
                if p.spec.node_name == self._node_name]
        # if there is no pods that means node is not up.
        # raise an error
        if not pods:
            pass

        # filter out all pods in kubernetes namespace.
        # we only want to remove user pods.
        pods = [p for p in pods if p.metadata.namespace != KUBE_NAMESPACE]
        return pods

    def _set_unschedulable(self, unschedulable):
        body = {
            "spec": {
                'unschedulable': unschedulable
            }
        }

        response = self._api.patch_node(self._node_name, body)
        return response

    def _delete_pod(self, pod, delete_options=None):
        name = pod.metadata.name
        namespace = pod.metadata.namespace
        if delete_options is None:
            delete_options = client.V1DeleteOptions()
        return self._api.delete_namespaced_pod(name, namespace, delete_options)

    def cordon(self):
        return self._set_unschedulable(True)

    def uncordon(self):
        return self._set_unschedulable(False)

    def drain(self, delete_options=None):
        self.cordon()
        pods = self._get_user_pods_for_node()
        response = []
        for pod in pods:
            response.append(self._delete_pod(pod))
        return response
