linstor --no-utf8 r list-volumes | grep \/ | awk '{ print $2 " " $4 }' | while read NN RN; do linstor r d $NN $RN; linstor rd d $RN; done
