while read line; do
  IFS='	' read -r -a array <<< "$line"
  TAG="${array[2]}"
  volttron-ctl stop --tag $TAG
done < $1
