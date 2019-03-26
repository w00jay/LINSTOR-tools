#
# HOW TO USE THIS
#
# If you aren't sure, ask Matt first.  J/K.  Ask Wooj for whatever.
#
# This was designed as to stand up LINSTOR volumes fast, for whatever reason.
# This will build up LINSTOR volumes on all known Nodes w/ supplied parameter(s) as
# resource volume name(s) on default pool.
#
# 1.  You need a LINSTOR cluster w/ Nodes and Storage Pools configured on those Nodes first.
#   Default resource size is set to 1Gib but feel free to change in KiB.
#
# 2. Configure the LOCAL LINSTOR URI, VOLUME GROUP name and RUN it.

import linstor
import pprint
import time
import re
import json
import sys

LVM = 'Lvm'
LVM_THIN = 'LvmThin'

#
# You probably DON'T want to change these, but I'm not stoppin'
#
DEFAULT_LINSTOR_URI = 'linstor://localhost'
DEFAULT_POOL = 'DfltStorPool'

#
# Please DO change this to reflect the Volume Group LINSTOR is going to sit on
#
VOL_GROUP = 'vg-35'
DEFAULT_RSC = 'LinstorRsc'
DEFAULT_RSC_SIZE = 1049000   # in KiB = 1GiB

# Hit it
lin = linstor.Linstor(DEFAULT_LINSTOR_URI)
lin.connect()
print(lin.connected)


def check_api_response(api_response):
  for apiresp in api_response:
    print(apiresp)
  return linstor.Linstor.all_api_responses_success(api_response)

def get_nodes():
    try:
        with linstor.Linstor(DEFAULT_LINSTOR_URI) as lin:

            # Get Node List
            node_list_reply = lin.node_list()
            assert node_list_reply, "Empty response"

            node_list = []
            if len(str(node_list_reply[0])) == 0:
                print("No LINSTOR nodes found on the network.")
            else:
                for node in node_list_reply[0].proto_msg.nodes:
                    # print('NODE: '+node.name+' = '+node.uuid+' = '+node.net_interfaces[0].address+'\n')
                    node_item = {}
                    node_item['node_name'] = node.name
                    node_item['node_uuid'] = node.uuid
                    node_item['node_address'] = node.net_interfaces[0].address
                    node_list.append(node_item)

            return node_list

    except Exception as e:
        print(str(e))

def get_spd():
    try:
        with linstor.Linstor(DEFAULT_LINSTOR_URI) as lin:

            # Storage Pool Definition List
            spd_list_reply = lin.storage_pool_dfn_list()
            assert len(str(spd_list_reply[0])), "Empty Storage Pool Definition list"

            node_list = spd_list_reply[0]
            # print(node_list.proto_msg)

            spd_list = []
            for node in node_list.proto_msg.stor_pool_dfns:
                spd_item = {}
                spd_item['spd_uuid'] = node.uuid
                spd_item['spd_name'] = node.stor_pool_name
                spd_list.append(spd_item)

            return spd_list

    except Exception as e:
        print(str(e))

def get_sp():

    try:
        with linstor.Linstor(DEFAULT_LINSTOR_URI) as lin:

            # Fetch Storage Pool List
            sp_list_reply = lin.storage_pool_list()
            assert len(str(sp_list_reply[0])), "Empty Storage Pool list"

            # print(sp_list_reply[0].proto_msg)

            sp_list = []
            node_count = 0
            for node in sp_list_reply[0].proto_msg.stor_pools:
                sp_node = {}
                # driver_pool_name = re.findall("StorDriver\/\w*\"\n\s*value: \"([0-9a-zA-Z\-_]+)\"", node)[0]
                sp_node['node_uuid'] = node.node_uuid
                sp_node['node_name'] = node.node_name
                sp_node['sp_uuid'] = node.stor_pool_uuid
                sp_node['sp_name'] = node.stor_pool_name

                for prop in node.props:
                    if "Vg" in prop.key:
                        sp_node['vg_name'] = prop.value  # node.props[0].value or sp_node['vg_name'][0].value
                    if "ThinPool" in prop.key:
                        print(prop.value+" is a thinpool")

                # Trying to optimize below causes incorrect result on py2.7
                sp_node['sp_free'] = round(node.free_space.free_capacity /
                                           ((1024 ** 3) / (1024.0 ** 1)), 2) # in GB

                #old node.driver == "LvmDriver":
                sp_node['driver_kind'] = node.provider_kind

                # print(node)

                if node.vlms:
                    print(node.vlms[0].device_path)
                else:
                    print('No volumes')

                sp_list.append(sp_node)

            print('\nFound '+str(len(sp_list))+' storage pools.')

            return sp_list

    except Exception as e:
        print(str(e))

def linstor_driver_init():
    try:
        with linstor.Linstor(DEFAULT_LINSTOR_URI) as lin:

            # Check for Storage Pool List
            sp_list = get_sp()
            # pprint.pprint(sp_list)

            # Get default Storage Pool Definition
            spd_default = VOL_GROUP

            if not sp_list:
                # print("No existing Storage Pools found")

                # Check for Ns
                node_list = get_nodes()
                # pprint.pprint(node_list)

                if len(node_list) == 0:
                    print("Error: No resource nodes available")  # Exception needed here

                # Create Storage Pool (definition is implicit)
                spd_name = get_spd()[0]['spd_name']

                pool_driver = LVM   # LVM_THIN

                if pool_driver == LVM:
                    driver_pool = VOL_GROUP
                elif pool_driver == LVM_THIN:
                    driver_pool = VOL_GROUP+"/"+spd_name

                for node in node_list:
                    lin.storage_pool_create(
                        node_name=node['node_name'],
                        storage_pool_name=spd_name,
                        storage_driver=pool_driver,
                        driver_pool_name=driver_pool)
                    print('Created Storage Pool for '+spd_name+' @ '+node['node_name']+' in '+driver_pool)

                # Ready to Move on
                return

            else:
                print("Found existing Storage Pools")
                # Ready to Move on
                return

    except Exception as e:
        print(str(e))

def linstor_deploy_resource(rsc_name=DEFAULT_RSC):

    try:
        with linstor.Linstor(DEFAULT_LINSTOR_URI) as lin:

            linstor_driver_init()

            # Check for RD
            rd_list = lin.resource_dfn_list()
            rsc_name_target = rsc_name

            print("No existing Resource Definition found.  Created a new one.")
            rd_reply = lin.resource_dfn_create(rsc_name_target)  # Need error checking
            print(check_api_response(rd_reply))
            rd_list = lin.resource_dfn_list()
            print("Created RD: "+str(rd_list[0].proto_msg))

            # Create a New VD
            vd_reply = lin.volume_dfn_create(
                rsc_name=rsc_name_target,
                size=int(DEFAULT_RSC_SIZE))  # size is in KiB
            print(check_api_response(vd_reply))
            print("Created VD: "+str(vd_reply[0].proto_msg))
            # print(rd_list[0])

            # Create RSC's
            sp_list = get_sp()
            # pprint.pprint(sp_list)

            for node in sp_list:
                rsc = linstor.linstorapi.ResourceData(
                    rsc_name=rsc_name_target,
                    node_name=node['node_name'])
                rsc_reply = lin.resource_create([rsc])
                print(check_api_response(rsc_reply))

    except Exception as e:
        print(str(e))

# This will spin up LINSTOR Resource Volumes named with supplied parameter(s) on all the known nodes.        
if __name__ == "__main__":
    if len(sys.argv) == 1:
        print('Please supply resource name(s) to create LINSTOR Volumes')
    else:
        for rsc_tgt in sys.argv[1:]:
            linstor_deploy_resource(rsc_name=str(rsc_tgt))
