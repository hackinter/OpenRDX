#!/bin/bash

# Define the repository link
REPO_LINK="https://github.com/hackinter/OpenRDX"

# Rename the openredirex.py file to open-rdx
mv openredirex.py open-rdx

# Move the open-rdx file to /usr/local/bin
sudo mv open-rdx /usr/local/bin/

# Make the open-rdx file executable
sudo chmod +x /usr/local/bin/open-rdx

# Remove the openredirex.pyc file if it exists
if [ -f openredirex.pyc ]; then
    rm openredirex.pyc
fi

# Clone the repository if it doesn't already exist
if [ ! -d "OpenRDX" ]; then
    git clone "$REPO_LINK"
fi

echo "OPEN-RDX has been installed successfully!"
