#!/usr/bin/env bash

# fifo name
fifo_name="/tmp/notimplemented_fifo"
notimplemented_output="/tmp/notimplemented_output"

# set trap to rm fifo_name at exit
trap "rm -f $fifo_name" EXIT

# if fifo not found, create
[ -p "$fifo_name" ] || mkfifo "$fifo_name"


exec 3< $fifo_name
# redirect fifo_name to fd 3

# (not required, but makes read clearer)
while :; do
    if read -r -n 1 -u 3 char; then
        if [ "$char" = 'q' ]; then
            # in case of debugging
            # printf "%s: quit command received\n" "$fifo_name"
            break
        fi
        echo $char >> $notimplemented_output
    fi
done

# reset fd 3 redirection
exec 3<&-

exit 0
