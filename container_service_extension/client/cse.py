# container-service-extension
# Copyright (c) 2017 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2-Clause

import os

import click
from vcd_cli.utils import stderr
from vcd_cli.utils import stdout
from vcd_cli.vcd import vcd


from container_service_extension.client import pks
from container_service_extension.client.cluster import Cluster
import container_service_extension.client.command_filter as cmd_filter
from container_service_extension.client.ovdc import Ovdc
from container_service_extension.client.system import System
import container_service_extension.client.utils as client_utils
from container_service_extension.exceptions import CseResponseError
from container_service_extension.logger import CLIENT_LOGGER
from container_service_extension.minor_error_codes import MinorErrorCode
from container_service_extension.server_constants import K8S_PROVIDER_KEY
from container_service_extension.server_constants import K8sProvider
from container_service_extension.server_constants import LocalTemplateKey
from container_service_extension.shared_constants import ComputePolicyAction
from container_service_extension.shared_constants import RESPONSE_MESSAGE_KEY
from container_service_extension.shared_constants import ServerAction
import container_service_extension.utils as utils


@vcd.group(short_help='Manage Native Kubernetes clusters')
@click.pass_context
def cse(ctx):
    """Manage Native Kubernetes clusters.

\b
Examples
    vcd cse version
        Display CSE version. If CSE version is displayed, then vcd-cli has
        been properly configured to run CSE commands.
    """


@cse.command(short_help='Display CSE version')
@click.pass_context
def version(ctx):
    """Display version of CSE plug-in."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    cse_info = utils.get_cse_info()
    ver_str = '%s, %s, version %s' % (cse_info['product'],
                                      cse_info['description'],
                                      cse_info['version'])
    stdout(cse_info, ctx, ver_str)
    CLIENT_LOGGER.debug(ver_str)


@cse.group(short_help='Manage native Kubernetes provider templates')
@click.pass_context
def template(ctx):
    """Manage native Kubernetes provider templates.

\b
Examples
    vcd cse template list
        Display templates that can be used by native Kubernetes provider.
    """
    pass


@template.command('list',
                  short_help='List native Kubernetes provider templates')
@click.pass_context
def list_templates(ctx):
    """Display templates that can be used by native Kubernetes provider."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        cluster = Cluster(client)
        result = cluster.get_templates()
        stdout(result, ctx, sort_headers=False)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cse.group('cluster', cls=cmd_filter.GroupCommandFilter,
           short_help='Manage Native Kubernetes clusters')
@click.pass_context
def cluster_group(ctx):
    """Manage Kubernetes clusters.

\b
Cluster names should follow the syntax for valid hostnames and can have
up to 25 characters .`system`, `template` and `swagger*` are reserved
words and cannot be used to name a cluster.
\b
Examples
    vcd cse cluster list
        Display clusters in vCD that are visible to the logged in user.
\b
    vcd cse cluster list -vdc ovdc1
        Display clusters in vdc 'ovdc1'.
\b
    vcd cse cluster create mycluster --network mynetwork
        Create a Kubernetes cluster named 'mycluster'.
        The cluster will have 2 worker nodes.
        The cluster will be connected to org VDC network 'mynetwork'.
        All VMs will use the default template.
        On create failure, the invalid cluster is deleted.
\b
    vcd cse cluster create mycluster --nodes 1 --enable-nfs \\
    --network mynetwork --template-name photon-v2 --template-revision 1 \\
    --cpu 3 --memory 1024 --storage-profile mystorageprofile \\
    --ssh-key ~/.ssh/id_rsa.pub --disable-rollback --vdc othervdc
        Create a Kubernetes cluster named 'mycluster' on org VDC 'othervdc'.
        The cluster will have 1 worker node and 1 NFS node.
        The cluster will be connected to org VDC network 'mynetwork'.
        All VMs will use the template 'photon-v2'.
        Each VM in the cluster will have 3 vCPUs and 1024mb of memory.
        All VMs will use the storage profile 'mystorageprofile'.
        The public ssh key at '~/.ssh/id_rsa.pub' will be placed into all
        VMs for user accessibility.
        On create failure, cluster will be left cluster in error state for
        troubleshooting.
\b
    vcd cse cluster resize mycluster --nodes 5 --network mynetwork
        Resize the cluster to have 5 worker nodes. On resize failure,
        returns cluster to original size.
        Nodes will be created from server default template at default revision.
        '--vdc' option can be used for faster command execution.
\b
    vcd cse cluster resize mycluster -N 10 --template-name my_template \\
    --template-revision 2 --disable-rollback
        Resize the cluster size to 10 worker nodes. On resize failure,
        cluster will be left cluster in error state for troubleshooting.
        Nodes will be created from template 'my_template' revision 2.
\b
    vcd cse cluster config mycluster > ~/.kube/config
        Write cluster config details into '~/.kube/config' to manage cluster
        using kubectl.
        '--vdc' option can be used for faster command execution.
\b
    vcd cse cluster info mycluster
        Display detailed information about cluster 'mycluster'.
        '--vdc' option can be used for faster command execution.
\b
    vcd cse cluster upgrade-plan mycluster
        Display available templates to upgrade to.
\b
    vcd cse cluster upgrade mycluster my_template 1
        Upgrade cluster 'mycluster' Docker-CE, Kubernetes, and CNI to match
        template 'my_template' at revision 1.
\b
    vcd cse cluster delete mycluster --yes
        Delete cluster 'mycluster' without prompting.
        '--vdc' option can be used for faster command execution.
    """
    pass


@cluster_group.command('list',
                       short_help='Display clusters in vCD that are visible '
                                  'to the logged in user')
@click.pass_context
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Filter list to show clusters from a specific org VDC')
@click.option(
    '-o',
    '--org',
    'org_name',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help="Filter list to show clusters from a specific org")
def list_clusters(ctx, vdc, org_name):
    """Display clusters in vCD that are visible to the logged in user."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        cluster = Cluster(client)
        if not client.is_sysadmin() and org_name is None:
            org_name = ctx.obj['profiles'].get('org_in_use')
        result = cluster.get_clusters(vdc=vdc, org=org_name)
        clusters = []
        for c in result:
            # TODO cluster api response keys need to be more well defined
            cluster = {
                'Name': c.get('name') or 'N/A',
                'VDC': c.get('vdc') or 'N/A',
                'Org': c.get('org_name') or 'N/A',
                'K8s Runtime': c.get('k8s_type') or 'N/A',
                'K8s Version': c.get('k8s_version') or 'N/A',
                'Status': c.get('status') or 'N/A',
                'Provider': c.get('k8s_provider') or 'N/A',
            }
            clusters.append(cluster)

        stdout(clusters, ctx, show_id=True, sort_headers=False)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cluster_group.command('delete',
                       short_help='Delete a Kubernetes cluster')
@click.pass_context
@click.argument('name', required=True)
@click.confirmation_option(prompt='Are you sure you want to delete the '
                                  'cluster?')
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specified org VDC')
@click.option(
    '-o',
    '--org',
    'org',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help='Restrict cluster search to specified org')
def cluster_delete(ctx, name, vdc, org):
    """Delete a Kubernetes cluster."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        cluster = Cluster(client)
        if not client.is_sysadmin() and org is None:
            org = ctx.obj['profiles'].get('org_in_use')
        result = cluster.delete_cluster(name, org, vdc)
        # result is empty for delete cluster operation on PKS-managed clusters.
        # In that specific case, below check helps to print out a meaningful
        # message to users.
        if len(result) == 0:
            click.secho(f"Delete cluster operation has been initiated on "
                        f"{name}, please check the status using"
                        f" 'vcd cse cluster info {name}'.", fg='yellow')
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cluster_group.command('create', short_help='Create a Kubernetes cluster')
@click.pass_context
@click.argument('name', required=True)
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Org VDC to use. Defaults to currently logged-in org VDC')
@click.option(
    '-N',
    '--nodes',
    'node_count',
    required=False,
    default=None,
    type=click.INT,
    help='Number of worker nodes to create')
@click.option(
    '-c',
    '--cpu',
    'cpu',
    required=False,
    default=None,
    type=click.INT,
    help='Number of virtual CPUs on each node')
@click.option(
    '-m',
    '--memory',
    'memory',
    required=False,
    default=None,
    type=click.INT,
    help='Megabytes of memory on each node')
@click.option(
    '-n',
    '--network',
    'network_name',
    default=None,
    required=False,
    help='Org vDC network name (Required)')
@click.option(
    '-s',
    '--storage-profile',
    'storage_profile',
    required=False,
    default=None,
    help='Name of the storage profile for the nodes')
@click.option(
    '-k',
    '--ssh-key',
    'ssh_key_file',
    required=False,
    default=None,
    type=click.File('r'),
    help='SSH public key filepath')
@click.option(
    '-t',
    '--template-name',
    'template_name',
    required=False,
    default=None,
    help='Name of the template to create new nodes from. '
         'If not specified, server default will be used '
         '(Must be used with --template-revision).')
@click.option(
    '-r',
    '--template-revision',
    'template_revision',
    required=False,
    default=None,
    help='Revision number of the template to create new nodes from. '
         'If not specified, server default will be used '
         '(Must be used with --template-revision).')
@click.option(
    '--enable-nfs',
    'enable_nfs',
    is_flag=True,
    help='Create 1 additional NFS node (if --nodes=2, then CSE will create '
         '2 worker nodes and 1 NFS node)')
@click.option(
    '--disable-rollback',
    'disable_rollback',
    is_flag=True,
    help='Disable rollback on cluster creation failure')
@click.option(
    '-o',
    '--org',
    'org_name',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help='Org to use. Defaults to currently logged-in org')
def cluster_create(ctx, name, vdc, node_count, network_name,
                   storage_profile, ssh_key_file, template_name,
                   template_revision, enable_nfs, disable_rollback, org_name,
                   cpu=None, memory=None):
    """Create a Kubernetes cluster (max name length is 25 characters)."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        if (template_name and not template_revision) or \
                (not template_name and template_revision):
            raise Exception("Both flags --template-name(-t) and "
                            "--template-revision (-r) must be specified.")

        client_utils.cse_restore_session(ctx)
        if vdc is None:
            vdc = ctx.obj['profiles'].get('vdc_in_use')
            if not vdc:
                raise Exception("Virtual datacenter context is not set. "
                                "Use either command 'vcd vdc use' or option "
                                "'--vdc' to set the vdc context.")
        if org_name is None:
            org_name = ctx.obj['profiles'].get('org_in_use')
        ssh_key = None
        if ssh_key_file is not None:
            ssh_key = ssh_key_file.read()

        client = ctx.obj['client']
        cluster = Cluster(client)
        result = cluster.create_cluster(
            vdc,
            network_name,
            name,
            node_count=node_count,
            cpu=cpu,
            memory=memory,
            storage_profile=storage_profile,
            ssh_key=ssh_key,
            template_name=template_name,
            template_revision=template_revision,
            enable_nfs=enable_nfs,
            rollback=not disable_rollback,
            org=org_name)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except CseResponseError as e:
        minor_error_code_to_error_message = {
            MinorErrorCode.REQUEST_KEY_NETWORK_NAME_MISSING: 'Missing option "-n" / "--network".', # noqa: E501
            MinorErrorCode.REQUEST_KEY_NETWORK_NAME_INVALID: 'Invalid or missing value for option "-n" / "--network".' # noqa: E501
        }
        e.error_message = \
            minor_error_code_to_error_message.get(
                e.minor_error_code, e.error_message)
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cluster_group.command('resize',
                       short_help='Resize the cluster to contain the '
                                  'specified number of worker nodes')
@click.pass_context
@click.argument('cluster_name', required=True)
@click.option(
    '-N',
    '--nodes',
    'node_count',
    required=True,
    default=None,
    type=click.INT,
    help='Desired number of worker nodes for the cluster')
@click.option(
    '-n',
    '--network',
    'network_name',
    default=None,
    required=False,
    help='Network name (Exclusive to native Kubernetes provider) (Required)')
@click.option(
    '-v',
    '--vdc',
    'vdc_name',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specified org VDC')
@click.option(
    '-o',
    '--org',
    'org_name',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help='Restrict cluster search to specified org')
@click.option(
    '--disable-rollback',
    'disable_rollback',
    is_flag=True,
    help='Disable rollback on node creation failure '
         '(Exclusive to native Kubernetes provider)')
@click.option(
    '-t',
    '--template-name',
    'template_name',
    required=False,
    default=None,
    help='Name of the template to create new nodes from. '
         'If not specified, server default will be used '
         '(Exclusive to native Kubernetes provider) '
         '(Must be used with --template-revision).')
@click.option(
    '-r',
    '--template-revision',
    'template_revision',
    required=False,
    default=None,
    help='Revision number of the template to create new nodes from. '
         'If not specified, server default will be used '
         '(Exclusive to native Kubernetes provider) '
         '(Must be used with --template-revision).')
@click.option(
    '-c',
    '--cpu',
    'cpu',
    required=False,
    default=None,
    type=click.INT,
    help='Number of virtual CPUs on each node '
         '(Exclusive to native Kubernetes provider)')
@click.option(
    '-m',
    '--memory',
    'memory',
    required=False,
    default=None,
    type=click.INT,
    help='Megabytes of memory on each node '
         '(Exclusive to native Kubernetes provider)')
@click.option(
    '-k',
    '--ssh-key',
    'ssh_key_file',
    required=False,
    default=None,
    type=click.File('r'),
    help='SSH public key filepath (Exclusive to native Kubernetes provider)')
def cluster_resize(ctx, cluster_name, node_count, network_name, org_name,
                   vdc_name, disable_rollback, template_name,
                   template_revision, cpu, memory, ssh_key_file):
    """Resize the cluster to contain the specified number of worker nodes.

    Clusters that use native Kubernetes provider can not be sized down
    (use 'vcd cse node delete' command to do so).
    """
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        if (template_name and not template_revision) or \
                (not template_name and template_revision):
            raise Exception("Both --template-name (-t) and "
                            "--template-revision (-r) must be specified.")

        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if not client.is_sysadmin() and org_name is None:
            org_name = ctx.obj['profiles'].get('org_in_use')

        ssh_key = None
        if ssh_key_file:
            ssh_key = ssh_key_file.read()
        cluster = Cluster(client)
        result = cluster.resize_cluster(
            network_name,
            cluster_name,
            node_count=node_count,
            org=org_name,
            vdc=vdc_name,
            rollback=not disable_rollback,
            template_name=template_name,
            template_revision=template_revision,
            cpu=cpu,
            memory=memory,
            ssh_key=ssh_key)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except CseResponseError as e:
        minor_error_code_to_error_message = {
            MinorErrorCode.REQUEST_KEY_NETWORK_NAME_MISSING: 'Missing option "-n" / "--network".', # noqa: E501
            MinorErrorCode.REQUEST_KEY_NETWORK_NAME_INVALID: 'Invalid or missing value for option "-n" / "--network".' # noqa: E501
        }
        e.error_message = \
            minor_error_code_to_error_message.get(
                e.minor_error_code, e.error_message)
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cluster_group.command('apply',
                       short_help='apply the configuration to Defined Entity'
                                  'Resource by filename; create resource if'
                                  ' doesn\'t exist')
@click.pass_context
@click.argument('cluster_config_file_path',
                metavar='CLUSTER_CONFIG_FILE_PATH',
                type=click.Path(exists=True))
def apply(ctx, cluster_config_file_path):
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        cluster = Cluster(client)
        cluster.apply(cluster_config_file_path)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cluster_group.command('upgrade-plan',
                       short_help='Display templates that the specified '
                                  'cluster can upgrade to')
@click.pass_context
@click.argument('cluster_name', required=True)
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specific org VDC')
@click.option(
    '-o',
    '--org',
    'org_name',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help="Restrict cluster search to specific org")
def cluster_upgrade_plan(ctx, cluster_name, vdc, org_name):
    """Display templates that the specified cluster can upgrade to."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        cluster = Cluster(client)
        if not client.is_sysadmin() and org_name is None:
            org_name = ctx.obj['profiles'].get('org_in_use')

        templates = cluster.get_upgrade_plan(cluster_name, vdc=vdc,
                                             org=org_name)
        result = []
        for template in templates:
            result.append({
                'Template Name': template[LocalTemplateKey.NAME],
                'Template Revision': template[LocalTemplateKey.REVISION],
                'Kubernetes': template[LocalTemplateKey.KUBERNETES_VERSION],
                'Docker-CE': template[LocalTemplateKey.DOCKER_VERSION],
                'CNI': f"{template[LocalTemplateKey.CNI]} {template[LocalTemplateKey.CNI_VERSION]}" # noqa: E501
            })

        if not templates:
            result = f"No valid upgrade targets for cluster '{cluster_name}'"
        stdout(result, ctx, sort_headers=False)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cluster_group.command('upgrade',
                       short_help="Upgrade cluster software to specified "
                                  "template's software versions")
@click.pass_context
@click.argument('cluster_name', required=True)
@click.argument('template_name', required=True)
@click.argument('template_revision', required=True)
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specific org VDC')
@click.option(
    '-o',
    '--org',
    'org_name',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help="Restrict cluster search to specific org")
def cluster_upgrade(ctx, cluster_name, template_name, template_revision,
                    vdc, org_name):
    """Upgrade cluster software to specified template's software versions.

    Affected software: Docker-CE, Kubernetes, CNI
    """
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        cluster = Cluster(client)
        if not client.is_sysadmin() and org_name is None:
            org_name = ctx.obj['profiles'].get('org_in_use')

        result = cluster.upgrade_cluster(cluster_name, template_name,
                                         template_revision, ovdc_name=vdc,
                                         org_name=org_name)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cluster_group.command('config', short_help='Display cluster configuration')
@click.pass_context
@click.argument('name', required=True)
@click.option(
    '-o',
    '--org',
    'org',
    required=False,
    default=None,
    metavar='ORG_NAME',
    help='Restrict cluster search to specified org')
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specified org VDC')
def cluster_config(ctx, name, vdc, org):
    """Display cluster configuration.

    To write to a file: `vcd cse cluster config mycluster > ~/.kube/my_config`
    """
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        cluster = Cluster(client)
        if not client.is_sysadmin() and org is None:
            org = ctx.obj['profiles'].get('org_in_use')
        cluster_config = cluster.get_cluster_config(name, vdc=vdc, org=org).get(RESPONSE_MESSAGE_KEY) # noqa: E501
        if os.name == 'nt':
            cluster_config = str.replace(cluster_config, '\n', '\r\n')

        click.secho(cluster_config)
        CLIENT_LOGGER.debug(cluster_config)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cluster_group.command('info',
                       short_help='Display info about a Kubernetes cluster')
@click.pass_context
@click.argument('name', required=True)
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specified org VDC')
@click.option(
    '-o',
    '--org',
    'org',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help='Restrict cluster search to specified org')
def cluster_info(ctx, name, org, vdc):
    """Display info about a Kubernetes cluster."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        cluster = Cluster(client)
        if not client.is_sysadmin() and org is None:
            org = ctx.obj['profiles'].get('org_in_use')
        cluster_info = cluster.get_cluster_info(name, org=org, vdc=vdc)
        stdout(cluster_info, ctx, show_id=True)
        CLIENT_LOGGER.debug(cluster_info)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cse.group('node',
           short_help='Manage nodes of clusters created by native '
                      'Kubernetes provider')
@click.pass_context
def node_group(ctx):
    """Manage nodes of clusters created by native Kubernetes provider.

These commands will only work with clusters created by native
Kubernetes provider.

\b
Examples
    vcd cse node create mycluster --network mynetwork
        Add 1 node to vApp named 'mycluster' on vCD.
        The node will be connected to org VDC network 'mynetwork'.
        The VM will use the default template.
\b
    vcd cse node create mycluster --nodes 2 --enable-nfs --network mynetwork \\
    --template-name photon-v2 --template-revision 1 --cpu 3 --memory 1024 \\
    --storage-profile mystorageprofile --ssh-key ~/.ssh/id_rsa.pub \\
        Add 2 nfs nodes to vApp named 'mycluster' on vCD.
        The nodes will be connected to org VDC network 'mynetwork'.
        All VMs will use the template 'photon-v2'.
        Each VM will have 3 vCPUs and 1024mb of memory.
        All VMs will use the storage profile 'mystorageprofile'.
        The public ssh key at '~/.ssh/id_rsa.pub' will be placed into all
        VMs for user accessibility.
\b
    vcd cse node list mycluster
        Displays nodes in 'mycluster'.
\b
    vcd cse node info mycluster node-xxxx
        Display detailed information about node 'node-xxxx' in cluster
        'mycluster'.
\b
    vcd cse node delete mycluster node-xxxx --yes
        Delete node 'node-xxxx' in cluster 'mycluster' without prompting.
    """
    pass


@node_group.command('info',
                    short_help='Display info about a node in a cluster that '
                               'was created with native Kubernetes provider')
@click.pass_context
@click.argument('cluster_name', required=True)
@click.argument('node_name', required=True)
@click.option(
    '-o',
    '--org',
    'org_name',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help='Restrict cluster search to specified org')
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specified org VDC')
def node_info(ctx, cluster_name, node_name, org_name, vdc):
    """Display info about a node in a native Kubernetes provider cluster."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        cluster = Cluster(client)

        if org_name is None and not client.is_sysadmin():
            org_name = ctx.obj['profiles'].get('org_in_use')
        node_info = cluster.get_node_info(cluster_name, node_name,
                                          org_name, vdc)
        stdout(node_info, ctx, show_id=True)
        CLIENT_LOGGER.debug(node_info)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@node_group.command('create',
                    short_help='Add node(s) to a cluster that was created '
                               'with native Kubernetes provider')
@click.pass_context
@click.argument('cluster_name', required=True)
@click.option(
    '-N',
    '--nodes',
    'node_count',
    required=False,
    default=1,
    type=click.INT,
    help='Number of nodes to create')
@click.option(
    '-c',
    '--cpu',
    'cpu',
    required=False,
    default=None,
    type=click.INT,
    help='Number of virtual CPUs on each node')
@click.option(
    '-m',
    '--memory',
    'memory',
    required=False,
    default=None,
    type=click.INT,
    help='Megabytes of memory on each node')
@click.option(
    '-n',
    '--network',
    'network_name',
    default=None,
    required=True,
    help='Network name')
@click.option(
    '-s',
    '--storage-profile',
    'storage_profile',
    required=False,
    default=None,
    help='Name of the storage profile for the nodes')
@click.option(
    '-k',
    '--ssh-key',
    'ssh_key_file',
    required=False,
    default=None,
    type=click.File('r'),
    help='SSH public key to connect to the guest OS on the VM')
@click.option(
    '-t',
    '--template-name',
    'template_name',
    required=False,
    default=None,
    help='Name of the template to create new nodes from. '
         'If not specified, server default will be used '
         '(Must be used with --template-revision).')
@click.option(
    '-r',
    '--template-revision',
    'template_revision',
    required=False,
    default=None,
    help='Revision number of the template to create new nodes from. '
         'If not specified, server default will be used '
         '(Must be used with --template-revision).')
@click.option(
    '--enable-nfs',
    'enable_nfs',
    is_flag=True,
    help='Enable NFS on all created nodes')
@click.option(
    '--disable-rollback',
    'disable_rollback',
    is_flag=True,
    help='Disable rollback on node deployment failure')
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specified org VDC')
@click.option(
    '-o',
    '--org',
    'org',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help='Restrict cluster search to specified org')
def create_node(ctx, cluster_name, node_count, org, vdc, cpu, memory,
                network_name, storage_profile, ssh_key_file, template_name,
                template_revision, enable_nfs, disable_rollback):
    """Add node(s) to a cluster that uses native Kubernetes provider."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        if (template_name and not template_revision) or \
                (not template_name and template_revision):
            raise Exception("Both --template-name (-t) and "
                            "--template-revision (-r) must be specified.")

        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if org is None and not client.is_sysadmin():
            org = ctx.obj['profiles'].get('org_in_use')
        cluster = Cluster(client)
        ssh_key = None
        if ssh_key_file is not None:
            ssh_key = ssh_key_file.read()
        result = cluster.add_node(
            network_name,
            cluster_name,
            node_count=node_count,
            org=org,
            vdc=vdc,
            cpu=cpu,
            memory=memory,
            storage_profile=storage_profile,
            ssh_key=ssh_key,
            template_name=template_name,
            template_revision=template_revision,
            enable_nfs=enable_nfs,
            rollback=not disable_rollback)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@node_group.command('list',
                    short_help='Display nodes of a cluster that was created '
                               'with native Kubernetes provider')
@click.pass_context
@click.argument('name', required=True)
@click.option(
    '-o',
    '--org',
    'org',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help='Restrict cluster search to specified org')
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specified org VDC')
def list_nodes(ctx, name, org, vdc):
    """Display nodes of a cluster that uses native Kubernetes provider."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if org is None and not client.is_sysadmin():
            org = ctx.obj['profiles'].get('org_in_use')
        cluster = Cluster(client)
        cluster_info = cluster.get_cluster_info(name, org=org, vdc=vdc)
        if cluster_info.get(K8S_PROVIDER_KEY) != K8sProvider.NATIVE:
            raise Exception("'node list' operation is not supported by non "
                            "native clusters.")
        all_nodes = cluster_info['master_nodes'] + cluster_info['nodes']
        stdout(all_nodes, ctx, show_id=True)
        CLIENT_LOGGER.debug(all_nodes)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@node_group.command('delete',
                    short_help='Delete node(s) in a cluster that was created '
                               'with native Kubernetes provider')
@click.pass_context
@click.argument('cluster_name', required=True)
@click.argument('node_names', nargs=-1, required=True)
@click.confirmation_option(prompt='Are you sure you want to delete '
                                  'the node(s)?')
@click.option(
    '-v',
    '--vdc',
    'vdc',
    required=False,
    default=None,
    metavar='VDC_NAME',
    help='Restrict cluster search to specified org VDC')
@click.option(
    '-o',
    '--org',
    'org',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help='Restrict cluster search to specified org')
def delete_nodes(ctx, cluster_name, node_names, org, vdc):
    """Delete node(s) in a cluster that uses native Kubernetes provider."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if not client.is_sysadmin() and org is None:
            org = ctx.obj['profiles'].get('org_in_use')
        cluster = Cluster(client)
        result = cluster.delete_nodes(cluster_name, list(node_names), org=org,
                                      vdc=vdc)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cse.group('system', short_help='Manage CSE service (system daemon)')
@click.pass_context
def system_group(ctx):
    """Manage CSE server remotely.

\b
Examples
    vcd cse system info
        Display detailed information of the CSE server.
\b
    vcd cse system enable --yes
        Enable CSE server without prompting.
\b
    vcd cse system stop --yes
        Stop CSE server without prompting.
\b
    vcd cse system disable --yes
        Disable CSE server without prompting.
    """
    pass


@system_group.command('info', short_help='Display info of CSE server')
@click.pass_context
def system_info(ctx):
    """Display CSE server info."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        system = System(client)
        result = system.get_info()
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@system_group.command('stop', short_help='Gracefully stop CSE server')
@click.pass_context
@click.confirmation_option(prompt='Are you sure you want to stop the server?')
def stop_service(ctx):
    """Stop CSE server."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        system = System(client)
        result = system.update_service_status(action=ServerAction.STOP)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@system_group.command('enable', short_help='Enable CSE server')
@click.pass_context
def enable_service(ctx):
    """Enable CSE server."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        system = System(client)
        result = system.update_service_status(action=ServerAction.ENABLE)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@system_group.command('disable', short_help='Disable CSE server')
@click.pass_context
def disable_service(ctx):
    """Disable CSE server."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        system = System(client)
        result = system.update_service_status(action=ServerAction.DISABLE)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@cse.group('ovdc', short_help='Manage Kubernetes provider for org VDCs')
@click.pass_context
def ovdc_group(ctx):
    """Manage Kubernetes provider for org VDCs.

All commands execute in the context of user's currently logged-in
organization. Use a different organization by using the '--org' option.


\b
Examples
    vcd cse ovdc enable ovdc1
        Set 'ovdc1' Kubernetes provider to be native (vCD).

\b
    vcd cse ovdc disable ovdc3
        Set 'ovdc3' Kubernetes provider to be none,
        which disables Kubernetes cluster deployment on 'ovdc3'.
\b
    vcd cse ovdc info ovdc1
        Display detailed information about ovdc 'ovdc1'.
\b
    vcd cse ovdc list
        Display ovdcs in vCD that are visible to the logged in user.
        vcd cse ovdc list
\b
        vcd cse ovdc list --pks-plans
            Displays list of ovdcs in a given org along with available PKS
            plans if any. If executed by System-administrator, it will
            display all ovdcs from all orgs.
    """
    pass


@ovdc_group.command('list',
                    short_help='Display org VDCs in vCD that are visible '
                               'to the logged in user')
@click.option(
    '-p',
    '--pks-plans',
    'list_pks_plans',
    is_flag=True,
    help="Display available PKS plans if org VDC is backed by "
         "Enterprise PKS infrastructure")
@click.pass_context
def list_ovdcs(ctx, list_pks_plans):
    """Display org VDCs in vCD that are visible to the logged in user."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        ovdc = Ovdc(client)
        result = ovdc.list_ovdc_for_k8s(list_pks_plans=list_pks_plans)
        stdout(result, ctx, sort_headers=False)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@ovdc_group.command('enable',
                    short_help='Set Kubernetes provider to be Native for an org VDC')  # noqa: E501
@click.pass_context
@click.argument('ovdc_name', required=True, metavar='VDC_NAME')
@click.option(
    '-o',
    '--org',
    'org_name',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help="Org to use. Defaults to currently logged-in org")
def ovdc_enable(ctx, ovdc_name, org_name):
    """Set Kubernetes provider for an org VDC."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if client.is_sysadmin():
            ovdc = Ovdc(client)
            if org_name is None:
                org_name = ctx.obj['profiles'].get('org_in_use')
            result = ovdc.update_ovdc_for_k8s(
                enable=True,
                ovdc_name=ovdc_name,
                org_name=org_name,
                k8s_provider=K8sProvider.NATIVE)
            stdout(result, ctx)
            CLIENT_LOGGER.debug(result)
        else:
            msg = "Insufficient permission to perform operation."
            stderr(msg, ctx)
            CLIENT_LOGGER.error(msg)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@ovdc_group.command('disable',
                    short_help='Disable Kubernetes cluster deployment for '
                               'an org VDC')
@click.pass_context
@click.argument('ovdc_name', required=True, metavar='VDC_NAME')
@click.option(
    '-o',
    '--org',
    'org_name',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help="Org to use. Defaults to currently logged-in org")
def ovdc_disable(ctx, ovdc_name, org_name):
    """Disable Kubernetes cluster deployment for an org VDC."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if client.is_sysadmin():
            ovdc = Ovdc(client)
            if org_name is None:
                org_name = ctx.obj['profiles'].get('org_in_use')
            result = ovdc.update_ovdc_for_k8s(enable=False,
                                              ovdc_name=ovdc_name,
                                              org_name=org_name)
            stdout(result, ctx)
            CLIENT_LOGGER.debug(result)
        else:
            msg = "Insufficient permission to perform operation."
            stderr(msg, ctx)
            CLIENT_LOGGER.error(msg)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@ovdc_group.command('info',
                    short_help='Display information about Kubernetes provider '
                               'for an org VDC')
@click.pass_context
@click.argument('ovdc_name', required=True, metavar='VDC_NAME')
@click.option(
    '-o',
    '--org',
    'org_name',
    default=None,
    required=False,
    metavar='ORG_NAME',
    help="Org to use. Defaults to currently logged-in org")
def ovdc_info(ctx, ovdc_name, org_name):
    """Display information about Kubernetes provider for an org VDC."""
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if client.is_sysadmin():
            ovdc = Ovdc(client)
            if org_name is None:
                org_name = ctx.obj['profiles'].get('org_in_use')
            result = ovdc.info_ovdc_for_k8s(ovdc_name, org_name)
            stdout(result, ctx)
            CLIENT_LOGGER.debug(result)
        else:
            msg = "Insufficient permission to perform operation"
            stderr(msg, ctx)
            CLIENT_LOGGER.error(msg)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@ovdc_group.group('compute-policy',
                  short_help='Manage compute policies for an org VDC')
@click.pass_context
def compute_policy_group(ctx):
    """Manage compute policies for org VDCs.

System administrator operations.

\b
Examples
    vcd cse ovdc compute-policy list --org ORG_NAME --vdc VDC_NAME
        List all compute policies for a specific ovdc in a specific org.
\b
    vcd cse ovdc compute-policy add POLICY_NAME --org ORG_NAME --vdc VDC_NAME
        Add a compute policy to a specific ovdc in a specific org.
\b
    vcd cse ovdc compute-policy remove POLICY_NAME --org ORG_NAME --vdc VDC_NAME
        Remove a compute policy from a specific ovdc in a specific org.
    """ # noqa: E501
    pass


@compute_policy_group.command('list', short_help='')
@click.pass_context
@click.option(
    '-o',
    '--org',
    'org_name',
    metavar='ORG_NAME',
    required=True,
    help="(Required) Org to use")
@click.option(
    '-v',
    '--vdc',
    'ovdc_name',
    metavar='VDC_NAME',
    required=True,
    help="(Required) Org VDC to use")
def compute_policy_list(ctx, org_name, ovdc_name):
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if not client.is_sysadmin():
            raise Exception("Insufficient permission to perform operation.")

        ovdc = Ovdc(client)
        result = ovdc.list_ovdc_compute_policies(ovdc_name, org_name)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@compute_policy_group.command('add', short_help='')
@click.pass_context
@click.argument('compute_policy_name', metavar='COMPUTE_POLICY_NAME')
@click.option(
    '-o',
    '--org',
    'org_name',
    metavar='ORG_NAME',
    required=True,
    help="(Required) Org to use")
@click.option(
    '-v',
    '--vdc',
    'ovdc_name',
    metavar='VDC_NAME',
    required=True,
    help="(Required) Org VDC to use")
def compute_policy_add(ctx, org_name, ovdc_name, compute_policy_name):
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if not client.is_sysadmin():
            raise Exception("Insufficient permission to perform operation.")

        ovdc = Ovdc(client)
        result = ovdc.update_ovdc_compute_policies(ovdc_name,
                                                   org_name,
                                                   compute_policy_name,
                                                   ComputePolicyAction.ADD,
                                                   False)
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


@compute_policy_group.command('remove', short_help='')
@click.pass_context
@click.argument('compute_policy_name', metavar='COMPUTE_POLICY_NAME')
@click.option(
    '-o',
    '--org',
    'org_name',
    metavar='ORG_NAME',
    required=True,
    help="(Required) Org to use")
@click.option(
    '-v',
    '--vdc',
    'ovdc_name',
    metavar='VDC_NAME',
    required=True,
    help="(Required) Org VDC to use")
@click.option(
    '-f',
    '--force',
    'remove_compute_policy_from_vms',
    is_flag=True,
    help="Remove the specified compute policy from deployed VMs as well. "
         "Affected VMs will have 'System Default' compute policy. "
         "Does not remove the compute policy from vApp templates in catalog. "
         "This VM compute policy update is irreversible.")
def compute_policy_remove(ctx, org_name, ovdc_name, compute_policy_name,
                          remove_compute_policy_from_vms):
    CLIENT_LOGGER.debug(f'Executing command: {ctx.command_path}')
    try:
        client_utils.cse_restore_session(ctx)
        client = ctx.obj['client']
        if not client.is_sysadmin():
            raise Exception("Insufficient permission to perform operation.")

        ovdc = Ovdc(client)
        result = ovdc.update_ovdc_compute_policies(ovdc_name,
                                                   org_name,
                                                   compute_policy_name,
                                                   ComputePolicyAction.REMOVE,
                                                   remove_compute_policy_from_vms) # noqa: E501
        stdout(result, ctx)
        CLIENT_LOGGER.debug(result)
    except Exception as e:
        stderr(e, ctx)
        CLIENT_LOGGER.error(str(e))


# Add-on CLI support for PKS container provider
cse.add_command(pks.pks_group)
