#!/bin/sh
pip3 install pyyaml
pip3 install git+https://github.com/huhabla/glances.git

# Store the glances start in the .bashrc of the pi user
cat << EOF >> $HOME/.bashrc
# Start the webservice only, if it is not already running
SERVICE="glances"
if pgrep -x "$SERVICE" >/dev/null
then
    echo "$SERVICE is running"
else
    echo "start $SERVICE"
    $HOME/.local/bin/glances -w&
fi
# Start the glances service in the terminal
$HOME/.local/bin/glances

EOF

