Place the ZeroMQ_EA compiled binaries here before building the Docker image:

- `ZeroMQ_EA.ex4`
- `ZeroMQ_EA.ex5`

These will be automatically copied into the `etradie-mt-node` Docker image during the build process, eliminating the need to manually mount them on the host VPS.


How it works automatically now: You no longer need to SSH into your VPS to upload files to /opt/ea/. All you need to do is place your compiled ZeroMQ_EA.ex4 and ZeroMQ_EA.ex5 files inside the docker/mt-node/ea/ folder in this repository before you build the image (docker build -t etradie-mt-node docker/mt-node/).

Docker will permanently embed them into the image. When the Engine daemon spins up new user containers, the EA binaries will already be safely isolated inside every single one of them. Fully automatic and 100% VPS-agnostic!