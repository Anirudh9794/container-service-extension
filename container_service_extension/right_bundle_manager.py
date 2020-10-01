# container-service-extension
# Copyright (c) 2020 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2-Claus

import pyvcloud.vcd.client as vcd_client

from container_service_extension.cloudapi.constants import CLOUDAPI_VERSION_1_0_0  # noqa: E501
from container_service_extension.cloudapi.constants import CloudApiResource
from container_service_extension.logger import NULL_LOGGER
from container_service_extension.logger import SERVER_CLOUDAPI_WIRE_LOGGER
import container_service_extension.pyvcloud_utils as vcd_utils
from container_service_extension.shared_constants import RequestMethod

CSE_NATIVE_RIGHT_BUNDLE_NAME = 'cse:nativeCluster Entitlement'


class RightBundleManager():
    def __init__(self, sysadmin_client: vcd_client.Client,
                 log_wire=False, logger_debug=NULL_LOGGER):
        vcd_utils.raise_error_if_not_sysadmin(sysadmin_client)
        self.logger_wire = SERVER_CLOUDAPI_WIRE_LOGGER \
            if log_wire else NULL_LOGGER
        self.logger_debug = logger_debug
        self.cloudapi_client = vcd_utils.get_cloudapi_client_from_vcd_client(
            sysadmin_client,
            logger_debug=self.logger_debug,
            logger_wire=self.logger_wire)

    def get_right_bundle_by_name(self, right_bundle_name):
        query_string = f"filter=name=={right_bundle_name}"
        response_body = self.cloudapi_client.do_request(
            method=RequestMethod.GET,
            cloudapi_version=CLOUDAPI_VERSION_1_0_0,
            resource_url_relative_path=f"{CloudApiResource.RIGHT_BUNDLES}?{query_string}")  # noqa: E501
        right_bundles = response_body['values']
        if right_bundles and len(right_bundles) > 0:
            return right_bundles[0]

    def publish_cse_right_bundle_to_tenants(self, right_bundle_id,
                                            org_ids):
        relative_url = \
            f"{CloudApiResource.RIGHT_BUNDLES}/{right_bundle_id}/tenants"
        payload = \
            {"values": [{"id": self.cloudapi_client.get_org_urn_from_id(org_id)} for org_id in org_ids]}  # noqa: E501
        return self.cloudapi_client.do_request(
            method=RequestMethod.PUT,
            cloudapi_version=CLOUDAPI_VERSION_1_0_0,
            resource_url_relative_path=relative_url,
            payload=payload)
