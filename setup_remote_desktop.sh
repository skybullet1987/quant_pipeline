#!/bin/bash
# Install XFCE Desktop and Chrome Remote Desktop on GCP
sudo apt-get update
sudo apt-get install -y xfce4 xfce4-goodies desktop-base dbus-x11 x11-xserver-utils
wget https://dl.google.com/linux/direct/chrome-remote-desktop_current_amd64.deb
sudo apt-get install -y ./chrome-remote-desktop_current_amd64.deb
rm chrome-remote-desktop_current_amd64.deb
sudo apt-get install -y google-chrome-stable
echo "Desktop environment installed successfully."
