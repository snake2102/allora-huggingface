## Install requirements
```
sudo apt update && sudo apt upgrade -y
sudo apt install jq -y

# install docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io
docker version

# install docker-compose
VER=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep tag_name | cut -d '"' -f 4)

curl -L "https://github.com/docker/compose/releases/download/"$VER"/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

## Install worker

A complete working example is provided in the `docker-compose.yml` file.

### Steps to Setup

1. **Clone the Repository**
   ```sh
    git clone https://github.com/snake2102/allora-huggingface.git
    ```
   ```sh
    cd allora-huggingface
    ```
2. **Copy and Populate Configuration**
    
    Copy the example configuration file and populate it with your variables:
    ```sh
    nano config.json
    ```

4. **Initialize Worker**
    
    Run the following commands from the project's root directory to initialize the worker:
    ```sh
    chmod +x init.config
    ./init.config
    ```
5. **Start the Services**
    
    Run the following command to start the worker node, inference, and updater nodes:
    ```sh
    docker compose up --build
    ```
    ```sh
    docker compose logs -f worker
    ```
6. **5. **Testing Inference Only**
