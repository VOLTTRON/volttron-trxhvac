d=`pwd`
while read line; do
  IFS='	' read -r -a array <<< "$line"
  export SOURCE="$d/${array[0]}"
  export CONFIG="$d/${array[1]}"
  export TAG="${array[2]}"
  echo $SOURCE $CONFIG $TAG
  cd $1
  . scripts/core/make-agent.sh
  cd $d
done < $2
