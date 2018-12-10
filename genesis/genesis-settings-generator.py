import os
from pyhocon import ConfigFactory, HOCONConverter
import subprocess
import string
import random


DEFAULT_NETWORK_BYTE = 'C'
DEFAULT_ACCOUNTS_COUNT = 1
DEFAULT_AVERAGE_BLOCK_DELAY = 10

DEFAULT_API_PORT = '6816'
DEFAULT_NETWORK_PORT = '6830'
DEFAULT_HEAP_SIZE = '2g'
DEFAULT_LOG_LEVEL = 'DEBUG'
DEFAULT_NETWORK = 'DEVNET'
DEFAULT_API_ENABLE = 'yes'
DEFAULT_AUTODETECT_ADDRESS = 'no'
TOKENS_SUPPLY = 10000000000000

addresses = []

network_byte = os.getenv('WAVES_NETWORK_BYTE', DEFAULT_NETWORK_BYTE)
accounts_count = os.getenv('WAVES_ACCOUNTS_COUNT', DEFAULT_ACCOUNTS_COUNT)
average_block_delay = os.getenv('WAVES_AVERAGE_BLOCK_DELAY', DEFAULT_AVERAGE_BLOCK_DELAY)

network_port = os.getenv('WAVES_NETWORK_PORT', DEFAULT_NETWORK_PORT)
api_port = os.getenv('WAVES_REST_API_PORT', DEFAULT_API_PORT)
heap_size = os.getenv('WAVES_HEAP_SIZE', DEFAULT_HEAP_SIZE)
log_level = os.getenv('WAVES_LOG_LEVEL', DEFAULT_LOG_LEVEL)
network = os.getenv('WAVES_NETWORK', DEFAULT_NETWORK)
autodetect_address = os.getenv('WAVES_AUTODETECT_ADDRESS', DEFAULT_AUTODETECT_ADDRESS)
WAVES__REST_API__ENABLE = os.getenv('WAVES__REST_API__ENABLE', DEFAULT_API_ENABLE)

if not isinstance(accounts_count, str):
    accounts_count = DEFAULT_ACCOUNTS_COUNT
else:
    accounts_count = int(accounts_count)


def generate_password(size=18, chars=string.ascii_letters + string.digits):
    return ''.join(random.choice(chars) for i in range(size))


def create_accounts():
    for k in range(0, accounts_count):
        new_seed = generate_password(100)
        seed = os.getenv('WAVES_ACCOUNT_' + str(k), new_seed)
        password = os.getenv('WAVES_ACCOUNT_PASSWORD_' + str(k), generate_password())
        if seed == '':
            seed = new_seed
        if password == '':
            password = generate_password()
        addresses.append({
            'seed': seed,
            'password': password
        })
    return addresses


def append_data_service(compose_content, nodes_list):
    compose_content += f"""
  data-service-explorer:
    image: wavesplatform/data-service-explorer
    environment:
      - WAVES_NETWORK_BYTE={network_byte}
      - WAVES_NODES_LIST={','.join(nodes_list)}
    depends_on:
      - node0
    restart: always
    ports:
      - "8080:3000"
    networks:
      default:
        aliases:
          - data-service-explorer
          - data-service-explorer.waves
networks:
  default:
    driver: bridge
    
"""
    return compose_content


def generate_compose(genesis_path):

    if not os.path.isdir("/waves-mnt/output"):
        os.mkdir("/waves-mnt/output")

    compose_content = "version: '3'\n\nservices:"

    nodes_list = []
    known_peers_list = []

    for k in range(0, accounts_count):
        known_peers_list.append(f"node{k}:6864")

    for k in range(0, accounts_count):
        if k > 0:
            if int(network_port) < 10000:
                instance_network_port = f"{k}{network_port}"
                instance_api_port = f"{k}{api_port}"
            else:
                instance_network_port = f"{str(int(network_port) + k)}"
                instance_api_port = f"{str(int(api_port) + k)}"
        else:
            instance_network_port = network_port
            instance_api_port = api_port

        node_config_path = f"/waves-mnt/output/node{k}/configs"
        if not os.path.isdir(node_config_path):
            os.makedirs(node_config_path, exist_ok=True)

        config_content = ConfigFactory.parse_file(genesis_path)
        config_content['waves']['network'] = ConfigFactory.from_dict({
            'known-peers': known_peers_list
        })

        config_content = HOCONConverter.convert(config_content, 'hocon')
        config_path = f"/waves-mnt/output/node{k}/configs/local.conf"
        with open(config_path, 'w') as config_file:
            config_file.write(config_content)

        nodes_list.append(f"node{k}:6869")
        compose_content += f"""
  node{k}:
    image: wavesplatform/node
    environment:
      - WAVES__NETWORK__NODE_NAME=node{k}
      - WAVES_WALLET_SEED={accounts[k]['seed']}
      - WAVES_WALLET_PASSWORD={accounts[k]['password']}
      - WAVES_VERSION=latest
      - WAVES_NETWORK={network}
      - WAVES_LOG_LEVEL={log_level}
      - WAVES_HEAP_SIZE={heap_size}
      - WAVES_AUTODETECT_ADDRESS={autodetect_address}
      - WAVES_AUTODETECT_ADDRESS_PORT={instance_network_port}
      - WAVES__NETWORK__DECLARED_ADDRESS=node{k}:6864
      - WAVES__REST_API__ENABLE={WAVES__REST_API__ENABLE}
      - WAVES__REST_API__PORT=6869
      - WAVES__REST_API__API_KEY_HASH=3z7LKtx9DwNVtEZ2whjZqrdZH8iWTZsdQYwWbgsxeXhm
      - WAVES__BLOCKCHAIN__CUSTOM__ADDRESS_SCHEME_CHARACTER={network_byte}
      - WAVES__MINER__QUORUM={accounts_count - 1}
      - WAVES__MINER__MIN_MICRO_BLOCK_AGE=2s
      - WAVES__MINER__MICRO_BLOCK_INTERVAL=3s
      - WAVES__MINER__INTERVAL_AFTER_LAST_BLOCK_THEN_GENERATION_IS_ALLOWED=999d
    restart: always
    networks:
      default:
        aliases:
          - node{k}
          - node{k}.waves
    ports:
      - "{instance_api_port}:6869"
      - "{instance_network_port}:6864"
    volumes:
      - ./node{k}:/waves"""

    compose_content = append_data_service(compose_content, nodes_list)

    compose_path = "/waves-mnt/output/docker-compose.yml"
    with open(compose_path, 'w') as compose_file:
        compose_file.write(compose_content)


if __name__ == "__main__":
    accounts = create_accounts()

    amount_per_user = TOKENS_SUPPLY / len(accounts)

    genesis_example_conf = "/waves-genesis/Waves/src/test/resources/genesis.example.conf"
    conf = ConfigFactory.parse_file(genesis_example_conf)

    conf['genesis-generator']['average-block-delay'] = str(average_block_delay) + 's'
    conf['genesis-generator']['network-type'] = network_byte

    distributions = dict()
    for x in range(0, len(accounts)):
        distributions[accounts[x]['seed']] = amount_per_user

    conf['genesis-generator']['distributions'] = ConfigFactory.from_dict(distributions)

    local_conf = HOCONConverter.convert(conf, 'hocon')

    genesis_conf_path = "/waves-genesis/Waves/src/test/resources/genesis.conf"

    with open(genesis_conf_path, 'w') as file:
        file.write(local_conf)

    with open('/waves-mnt/genesis.conf', 'w') as file:
        file.write(local_conf)

    run_command = f"test:runMain tools.GenesisBlockGenerator {genesis_conf_path}"
    result_lines = subprocess.run(['sbt', run_command], universal_newlines=True, stdout=subprocess.PIPE,
                                  cwd="/waves-genesis/Waves")

    lines = result_lines.stdout.splitlines()

    genesis_data = []
    start_index = -1
    end_index = len(lines)

    for idx, line in enumerate(lines):
        line = str(line).replace('[0minfo', '')
        line = line.replace('[0m', '')
        line = line.replace('[]', '')
        if "genesis {" in line:
            print("Found start line: ", idx)
            start_index = idx
            end_index = start_index + 9 + accounts_count

        if start_index != -1 and start_index <= idx <= end_index:
            genesis_data.append(line)

    genesis_data = "\n".join(genesis_data)

    print('Genesis is ready')

    config = f"""waves {{
        blockchain {{
          custom {{
            {genesis_data}
          }}
        }}
      }}
      kamon{{
        enable = no
      }}"""
    genesis_file = "/waves-mnt/waves-config-genesis.conf"
    with open(genesis_file, 'w') as file:
        file.write(config)

    generate_compose(genesis_file)
    print('Genesis and compose files are ready to go!')
