# README

This project brings up the following environment: 

1. scale-agentex
    - [scale-agentex backend](scale-agentex/agentex/README.md)
    - [scale-agentex ui](scale-agentex/agentex-ui/README.md)
2. web-agent: an agent that leverages the openai MCP server to get a web search tool to search the web
    - [web-search](web_search/README.md)

All of these components are dockerized. Once you bring them up you can browse to [https://localhost:3000](https://locahost:3000) to interact with the agents. 

# Quick Start

This quick start assumes that you have docker installed and are able to run run containers and build them. If you are not sure, please go to the sections for [Mac](#mac-setup-guide) or [Windows](#windows-setup-guide). 

## Initialize Submodule 

Depending on how you clone this repo, you may need to initialize the scale-agentex submodule: 

```bash

git submodule update --init --recursive

```

## Set the .env file

To connect to the LLMs, we run through the SGP gateway. You will need to specify the following for the agents to actually communicated with OpenAI/Claude/Gemeni/etc: 

```bash
SGP_API_KEY=
SGP_BASE_URL=
SGP_ACCOUNT_ID=
```

These should go in a file called `.env` in the root directory (alonside your docker-compose file). 

## Build "Slim" version

When building on Z-Scaler, pulling in dependencies can take a long time. To get around this, we have provided a "slim" build. This is defined by docker-compose.slim.yaml and the Dockerfile.slim versions in the various folders. These rely on building an intermediate container defined by [Dockerfile.base](Dockerfile.base) and publishing it to the local repository as `local-base:latest`. 

To make this easy to run we have provided two scripts: [run_agentex.sh](run_agentex.sh) and [run_agentex.ps1](run_agentex.ps1) for mac and windows, respectivly. Both of these build the intermediate container then bring the whole docker-compose up. 

### Mac

To bring this up on mac simply run

```bash
bash run_agentex.sh
```

This assumes that you have docker-compose available in your CLI. If instead you are using podman, simply run: 

```bash
bash run_agentex.sh --podman
```

### Windows

To bring this up on a Windows Machine simply run: 

```powershell
.\run_agentex.ps1
```

Similarly, this assumes that you are using docker-compose to bring this up. If you are using podman, you can run: 

```powershell
.\run_agentex.ps1 -Podman
```

## Build the full version

To build the full version (I.E. without an intermdiate docker container), you can use the [docker-compose.yaml](docker-compose.yaml) file. This will not build and intermediate container and may take a long time to build. 

Run the following from your terminal (same for windows or mac): 

```bash
docker-compose up --build
```

or if using podman

```bash
podman compose up --build
```

## Trouble shooting

If you run into any trouble, the best course of action is to do the following: 

1. bring the docker-compose down with `docker compose down --volumes`
2. prune the entire docker system with `docker system prune -a`
    - Note: This will remove all containers and volumes that are not running. Use with caution if you have other docker projects running. 

# Setup Guides

Below are the setup guides to get docker running on a local system. Our preferred method is rancher or podman as it does not have any licensing dependencies. 

## Mac Setup Guide

### Podman

Follow the guide at [podman.io](https://podman.io/docs/installation).

### Rancher

#### Use brew (preferred)

Run the following: 

```bash
brew install --cask rancher
```

#### Download from the web

For contractors, it may be possible to download and install from the web. Follow the instructions here: 

[https://docs.rancherdesktop.io/getting-started/installation/](https://docs.rancherdesktop.io/getting-started/installation/)

## Windows Setup Guide

### Podman

Follow the guide at [podman.io](https://podman.io/docs/installation).

### Rancher

Rancher for Windows. You will need to install wsl and also rancher by following this guide: 

[Windows Rancher Install Guide](https://docs.rancherdesktop.io/getting-started/installation/#windows)
