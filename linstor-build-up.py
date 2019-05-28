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

import jsons
import pprint
import sys

LVM = 'LVM'
LVM_THIN = 'LVM_THIN'
ZFS = 'ZFS'
ZFS_THIN = 'ZFS_THIN'
DISKLESS = 'DISKLESS'

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


def check_api_response(api_response, noerror_only=False):
    if noerror_only:
        # Checks if none of the replies has an error
        return linstor.all_api_responses_no_error(api_response)
    else:
        # Check if all replies are success
        pass

def get_nodes():
    try:
        lin = linstor.Linstor(DEFAULT_LINSTOR_URI)
        lin.connect()
        # Get Node List
        node_list_reply = jsons.dump(lin.node_list()[0].nodes)
        assert node_list_reply, "No LINSTOR nodes found"

        node_list = []
        if node_list_reply:
            for node in node_list_reply:
                node_item = {}
                node_item["node_name"] = node["name"]
                # TODO (wap): Remove after testing
                # node_item["node_uuid"] = node['uuid']
                node_item["node_address"] = (
                    node["net_interfaces"][0]["address"])
                node_list.append(node_item)

        lin.disconnect()
        return node_list

    except Exception as e:
        print(str(e))


def get_spd():
    try:
        lin = linstor.Linstor(DEFAULT_LINSTOR_URI)
        lin.connect()
        # Storage Pool Definition List
        spd_list_reply = jsons.dump(
            lin.storage_pool_dfn_list()[0].storage_pool_definitions)
        assert len(str(spd_list_reply[0])), "Empty Storage Pool Definition list"

        node_list = spd_list_reply[0]
        # print(node_list.proto_msg)

        spd_list = []
        for spd in spd_list_reply:
            spd_list.append(spd["name"])

        lin.disconnect()
        return spd_list

    except Exception as e:
        print(str(e))


def get_sp():
    try:
        lin = linstor.Linstor(DEFAULT_LINSTOR_URI)
        lin.connect()
        # Fetch Storage Pool List
        sp_list_reply = jsons.dump(lin.storage_pool_list()[0].storage_pools)
        assert sp_list_reply, "Empty Storage Pool list"

        print(len(sp_list_reply))

        sp_diskless_list = []
        sp_list = []
        node_count = 0
        if sp_list_reply:
            for node in sp_list_reply:
                
                print(node["node_name"])
                sp_node = {}
                sp_node['node_name'] = node["node_name"]
                sp_node['sp_uuid'] = node["uuid"]
                sp_node['sp_name'] = node["name"]

                if node["provider_kind"] == DISKLESS:
                    diskless = True
                else:
                    diskless = False

                # Driver selection
                if node["provider_kind"] == LVM:
                    sp_node['driver_name'] = LVM
                elif node["provider_kind"] == LVM_THIN:
                    sp_node['driver_name'] = LVM_THIN
                elif node["provider_kind"] == ZFS:
                    sp_node['driver_name'] = ZFS
                elif node["provider_kind"] == ZFS_THIN:
                    sp_node['driver_name'] = ZFS_THIN
                else:
                    sp_node['driver_name'] = str(node["provider_kind"])

                if diskless:
                    sp_diskless_list.append(sp_node)
                else:
                    sp_list.append(sp_node)
                node_count += 1

                print(sp_node)

        # Add the diskless nodes to the end of the list
        if sp_diskless_list:
            sp_list.extend(sp_diskless_list)

        print('\nFound '+str(len(sp_list))+' storage pools.')

        lin.disconnect()
        pprint.pprint(sp_list)
        return sp_list

    except Exception as e:
        print(str(e))


def linstor_driver_init():
    try:
        lin = linstor.Linstor(DEFAULT_LINSTOR_URI)
        lin.connect()
        # Check for Storage Pool List
        sp_list = get_sp()
        # pprint.pprint(sp_list)

        # Get default Storage Pool Definition
        spd_default = VOL_GROUP

        if not sp_list:
            print("No existing Storage Pools found")

            # Check for Ns
            node_list = get_nodes()
            # pprint.pprint(node_list)

            if len(node_list) == 0:
                print("Error: No resource nodes available")  # Exception needed here

            # Create Storage Pool (definition is implicit)
            spd_name = get_spd()[0]

            pool_driver = LVM_THIN   # LVM_THIN

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
            lin.disconnect()
            return

        else:
            print("Found existing Storage Pools")
            # Ready to Move on
            lin.disconnect()
            return

    except Exception as e:
        print(str(e))


def linstor_deploy_resource(rsc_name=DEFAULT_RSC):
    try:
        lin = linstor.Linstor(DEFAULT_LINSTOR_URI)
        lin.connect()
        linstor_driver_init()

        # Check for RD
        # rd_list = lin.resource_dfn_list()
        # rsc_name_target = rsc_name
        rd_reply = lin.resource_dfn_create(rsc_name)  # Need error checking
        print(check_api_response(rd_reply))
        rd_list = lin.resource_dfn_list()
        print("Created RD")

        # Create a New VD
        vd_reply = lin.volume_dfn_create(
            rsc_name=rsc_name,
            size=int(DEFAULT_RSC_SIZE))  # size is in KiB
        print(check_api_response(vd_reply))
        print("Created VD: "+str(vd_reply))

        # Create RSC's
        sp_list = get_sp()
        pprint.pprint(sp_list)

        for node in sp_list:
            if node["driver_name"] == "DISKLESS":
                is_diskless = True
            else:
                is_diskless = False

            new_rsc = linstor.ResourceData(rsc_name=rsc_name,
                                           node_name=node["node_name"],
                                           storage_pool=node["sp_name"],
                                           diskless=is_diskless)

            rsc_reply = lin.resource_create([new_rsc], async_msg=False)
            print("RSC Create: " + str(check_api_response(rsc_reply)))

        lin.disconnect()
        return
    except Exception as e:
        print(str(e))


# This will spin up LINSTOR Resource Volumes named with supplied parameter(s) on all the known nodes.
if __name__ == "__main__":
    if len(sys.argv) == 1:
        print('Please supply resource name(s) to create LINSTOR Volumes')
    else:
        for rsc_tgt in sys.argv[1:]:
            linstor_deploy_resource(rsc_name=str(rsc_tgt))
            print('Finished deploying ' + str(rsc_tgt))
        print('Finshed deploying all resources')
