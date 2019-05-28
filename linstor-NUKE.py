# 
# HOW TO USE THIS
# 
# If you aren't sure, ask Matt first.  J/K.  Ask Wooj for whatever.  
#
# This was designed as to tear down ALL KNOWN LINSTOR RESOURCES on the network.
# This is equavalent of 'rm -rf *' AND DOES NOT ASK YOU FOR CONFIRMATION OR HELP.  
# It's a mean grown-up and don't come back for crying if you deploy it and ruins your day.
# 
# 1.  You need a LINSTOR cluster w/ Nodes and Storage Pools configured on those Nodes first.
#
# 2. Configure the LOCAL LINSTOR URI, VOLUME GROUP name and RUN it.
# 
# It DOES NOT run FAST.  Takes about (num of nodes * num of resources) seconds to run.  I can't help it for 
# the moment as LINSTOR goes nuts if I fire-hose resource delete commands.  
# 
# PS.  It only removes volume 0 of any Resource Definitions.  Let me know if you need me to fix it.  -w-

import linstor

import jsons
import pprint
import sys
import time

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

def nuke():

    with linstor.Linstor(DEFAULT_LINSTOR_URI) as lin:

        # Nuke Resources
        rsc_reply = jsons.dump(lin.resource_list()[0].resources)

        if rsc_reply:
            print(rsc_reply)

            for rsc in rsc_reply:
                print(rsc["_rest_data"]["name"]+' at '+rsc["_rest_data"]["node_name"])

                lin.resource_delete(
                    node_name = rsc["_rest_data"]["node_name"],
                    rsc_name = rsc["_rest_data"]["name"])
                time.sleep(1)

                rsc_dfn_list = jsons.dump(
                    lin.resource_dfn_list()[0].resource_definitions)

                print(rsc_dfn_list)
                for rsc_dfn in rsc_dfn_list:
                    print(rsc_dfn["name"])

                    # Delete VD
                    print('Deleting Volume Definition for '+rsc_dfn["name"])
                    
                    # TODO: Need work here for volume number
                    api_reply = lin.volume_dfn_delete(rsc_dfn["name"], 0)
                    print(api_reply)
                    time.sleep(1)

                    # Delete RD
                    print('Deleting Resource Definition for '+rsc_dfn["name"])
                    api_reply = lin.resource_dfn_delete(rsc_dfn["name"])
                    print(api_reply)
        else:
            print('NO RSCs to delete')

        #linstor_teardown_resource

#
# Are you sure?
#
if __name__ == "__main__":
    if len(sys.argv) == 1:
        print('Please specify parameter -Y to confirm')
    else:
        if str(sys.argv[1]) == "-Y":
            nuke()
        else:
            print('Please specify parameter -Y to confirm')
