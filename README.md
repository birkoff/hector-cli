# Hector CLI (HeCLI)
My personal CLI ToolKit

## Table of Contents
This documentation may become out out of date. You can always check the commands using `neotk <command> --help`.

### Installation
```
brew install python3
pip3 install -r requirements.txt

# Add the PATH to ~/.bash_profile
export PATH=$PATH:<path to repo>
```

### Commands
- [`neotk assume --help`](docs/commands/assume.md)
- [`neotk cloudhsm --help`](docs/commands/cloudhsm.md)
- [`neotk deploy_token --help`](docs/commands/deploy_token.md)
- [`neotk deploy_uservice --help`](docs/commands/deploy_uservice.md)
- [`neotk export_users --help`](docs/commands/export_users.md)
- [`neotk fetch_repos --help`](docs/commands/fetch_repos.md)
- [`neotk hello_world --help`](docs/commands/hello_world.md)

### Other
- [Extending the Toolkit](docs/extending.md)

### Great Third Party Tools
* [awslogs](https://github.com/jorgebastida/awslogs/blob/master/README.rst) - Easy access to cloudwatch logs
