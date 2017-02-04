# tools-alpha
Tools for the DGU alpha

## Vagrant machine setup

``` bash
git clone git@github.com:datagovuk/tools_alpha.git
cd tools_alpha
vagrant up
vagrant ssh
sudo apt-get update
sudo apt-get install -y python-pip python-virtualenv git-core python3-dev
```

## Python environment
```
# Make and activate a virtualenv for Python 3
virtualenv --no-site-packages --distribute -p /usr/bin/python3.4 ~/venv
. ~/venv/bin/activate
cd /vagrant
pip install -r requirements.txt

# niceties, if on dedicated VM:
echo ". ~/venv/bin/activate" >> ~/.bashrc
echo "cd /vagrant" >> ~/.bashrc
```

## Location data

Basic:
```
python3 /vagrant/location_data/location_data.py publish_data
```

Preserving pk values:
```
# on the host machine (vagrant)
export PUBLISH_ALPHA_REPO=~/v-publish-alpha
export TOOLS_ALPHA_REPO=~/v-tools_alpha
cd $PUBLISH_ALPHA_REPO
git pull
cp $PUBLISH_ALPHA_REPO/src/datasets/fixtures/locations.json $TOOLS_ALPHA_REPO/location_data/existing_locations.json

# in the VM
python3 /vagrant/location_data/location_data.py publish_data --existing-locations /vagrant/location_data/existing_locations.json --output_fpath /vagrant/location_data/locations.json

# on the host machine
cp $TOOLS_ALPHA_REPO/location_data/locations.json $PUBLISH_ALPHA_REPO/src/datasets/fixtures/locations.json
cd $PUBLISH_ALPHA_REPO
git checkout -b locations-json-update
git commit -a -m 'Updated locations.json'
git push -u origin locations-json-update
# Create PR at https://github.com/datagovuk/publish_data_alpha/compare/locations-json-update?expand=1


## Pubinfo - Publisher information
see pubinfo/README.md