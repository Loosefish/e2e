#!/bin/sh
addr="$(hostname --ip-address|tr -d ' ')"
port=$(( $(date +%s) % 3000 + 1025 ))
music="$1"


start_first() {
	cmd="python3 main.py $music $addr $port $(( port + 1 ))"
	tmux new-window -n $1 "python3 main.py $music $addr $port $(( port + 1 ))"
}


start_next() {
	sleep 2
	port=$(( port + 2 ))
	cmd="python3 main.py $music $addr $port $(( port + 1 )) -c \"$addr:$(( port - 2 ))\""
	tmux split-window -t:$1 "$cmd"
}


start_first e2e_1
start_next e2e_1
start_next e2e_1
start_next e2e_1
tmux select-layout -t:e2e_1 tiled
