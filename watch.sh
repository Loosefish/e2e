#!/bin/bash
sock=/tmp/$(ls -c /tmp|grep "e2e-mpd"|head -n 1)/socket
echo $sock
if command -v mpc; then
	playlist="mpc -h $sock -f '%position%  %artist%  %title%  (%time%)' playlist"
else
	playlist="echo playlist|nc -U $sock|tail -n +2|head -n -1|sed -e 's/:file:/  /'"
fi
watch -n 1 -t ${playlist}
