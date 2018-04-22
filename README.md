# Sonification of netflow traffic - a netflow collector that processes and sends flows to be played by sonic-pi via the OSC protocol

This script receives V9 netflow, aggregates it and forwardes it to SonicPi via the OSC protocol, creating beautiful melodies and easing the difficult task of network monitoring and DDoS detection.
As the traffic increases the music will grow louder, hinting that an attack might be currently in progress.

# Install prerequisites
pip install -r requirements.txt

# Usage:
Make sure you use python3
--port -P	Port address for the netflow collector
--host -H	IP address for the netflow collector
--poll -I	Poll interval
--sonicpihost -S	IP address to send flows to over OSC
--sonicpiport -R	Port address to send flows to over OSC
--graphics -G	Display graphics

To run the Sonic Pi player, you'll need to use the "hackatone.rb" script located under the sonic_pi dir.
Inside the script you'll find commented-out pieces of code you can use if you wish to use sound samples instead of synthesizers. If you wish to do so, you'll need to download a program written by Robin Newman: (https://gist.github.com/rbnpi/992bcbdec785597453bf).

For the MakeyMakey integration: 
Under the makey_makey folder you'll find the "makey_makey_2_osc.ino" file – that’s the code that should be loaded into the WeMos D1 to transform signals from MakeyMakey into OSC messages and send them to the device running Sonic Pi.