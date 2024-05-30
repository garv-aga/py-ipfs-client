# IPFS Client

A Python client for interacting with IPFS and Filecoin using an asynchronous interface. This client supports adding data to IPFS, pinning, remote pinning services, archival and unpinning to save bandwith, and retrieving data from Filecoin using Lassie.

## Features

- Add JSON or string data to IPFS.
- Archive data to Filecoin via lighthouse.storage.
- Retrieve data from Filecoin via Lassie.
- Unpin data from IPFS.
- Get proof of storage from Filecoin().

## Installation

This project uses [IPFS]() and [Lassie]() for its core functionality and [Poetry](https://python-poetry.org/) for dependency management.

Follow the steps here to install IPFS: [Link](https://docs.ipfs.tech/install/command-line/#install-official-binary-distributions)

Follow the steps here to install Lassie: [Link](https://docs.filecoin.io/basics/how-retrieval-works/basic-retrieval#install-lassie)

To install the dependencies, run:

```sh
$ pip install poetry
$ poetry install
```

## Configuration

1. Start the IPFS Node
   ```sh
   $ ipfs daemon
   ```
2. Start the Lassie Service
   ```sh
    $ lassie daemon
   ```

Note the ports for both the service and update them respectively.

By Default:

```python
ipfs_url = os.getenv('IPFS_URL', 'http://localhost:5001') # in tests directory
```

```python
url = f'http://127.0.0.1:36711/ipfs/{cid}?filename={outputfname}' # in main.py:248
```

3. Update the lighthouse.storage API key for archival. Generate an API key [here](https://files.lighthouse.storage/dashboard/apikey)
   ```python
   headers = {'Authorization': f'Bearer YOUR_API_KEY'} # in main.py:228
   ```

## Usage

The usage of each function is defined in the tests folder.

```sh
$ poetry run python -m ipfs_client.tests.<FILE_NAME>
```

Update FILE_NAME with the respective implementation you want to check.

## License

This project is an enhancement to [Powerloom's IPFS Client](https://github.com/PowerLoom/py-ipfs-client) made during ETH Global's [HackFS 2024](https://ethglobal.com/events/hackfs2024)

`` This `README.md` provides a comprehensive guide to understanding, configuring, and using the IPFS client, including how to run the provided tests. Adjust paths and variables as needed to match your project's specific configuration and requirements. ``
