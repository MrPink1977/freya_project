# Freya Project

This is the documentation for the Freya Project. It explains the purpose of the project, how to set it up, and how to use it.

## Table of Contents

- [Installation](#installation)
  - [System Dependencies](#system-dependencies)
  - [Python Dependencies](#python-dependencies)
  - [Docker Installation](#docker-installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Installation

### System Dependencies

Before installing Python dependencies, you need to install system-level audio libraries:

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-dev build-essential
```

#### Linux (Fedora/RHEL/CentOS)

```bash
sudo dnf install -y portaudio-devel python3-devel gcc gcc-c++ make
```

#### macOS

Using Homebrew:

```bash
brew install portaudio
```

#### Windows

On Windows, the Python packages typically include pre-built binaries, so no additional system dependencies are required. However, ensure you have:

1. Visual C++ Redistributable installed (usually comes with Windows)
2. Python 3.8 or later

### Python Dependencies

After installing system dependencies, install Python dependencies:

```bash
# Clone the repository
git clone https://github.com/MrPink1977/freya_project.git
cd freya_project

# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### Docker Installation

For a consistent development environment without manual dependency installation, use Docker:

1. **Build the Docker image:**

```bash
docker build -t freya-project .
```

2. **Run the container:**

```bash
docker run -it --rm \
  --device /dev/snd \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/data:/app/data \
  freya-project
```

Note: The `--device /dev/snd` flag provides access to audio devices on Linux. For macOS and Windows, Docker audio support may require additional configuration.

3. **Run with custom configuration:**

```bash
docker run -it --rm \
  --device /dev/snd \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/data:/app/data \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  freya-project
```

## Usage

Run the project using the following command:

```bash
python main.py
```

## Contributing

We welcome contributions from the community! Please read the contribution guidelines before submitting a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

*Updated on: 2025-11-16 17:54:30*