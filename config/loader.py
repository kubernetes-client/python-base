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

import logging

from .incluster_config import load_incluster_config
from .kube_config import load_kube_config

LOGGER = logging.getLogger(__name__)


def load(incluster_config_args=None, kube_config_args=None):
    """
    Loads authentication and cluster information

    Tries in this order:
    - in-cluster config
    - kube-config file
    and stores them in kubernetes.client.configuration.

    :param incluster_args: Arguments for load_incluster_config.
    :param kube_args: Arguments for load_kube_config.
    """

    try:
        load_incluster_config(**(incluster_config_args or {}))
    except (FileNotFoundError, ConfigException) as err:
        LOGGER.debug("Failed to load in-cluster config: %s", err)
        load_kube_config(**(kube_config_args or {}))
