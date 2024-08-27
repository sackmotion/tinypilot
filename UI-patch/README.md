sudo cp patch-UI.diff /opt 
cd /opt
sudo patch -p0 --run-dry < patch-UI.diff

if all good apply :

sudo patch -p0  < patch-UI.diff


