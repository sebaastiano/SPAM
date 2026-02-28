# Running with Ollama

Source: http://docs.datapizza.ai/0.0.9/Guides/Clients/local_model/

Datapizza AI supports running with local models through Ollama, providing you with complete control over your AI infrastructure while maintaining privacy and reducing costs.

---

## Prerequisites

Before getting started, you'll need to have Ollama installed and running on your system.

### Installing Ollama

1. Download and Install Ollama
2. Visit [ollama.ai](https://ollama.ai/) and download the installer for your operating system
3. Follow the installation instructions for your platform
4. Start Ollama Service

```bash
# Ollama typically starts automatically after installation
# If not, you can start it manually:
ollama serve
```

5. Pull a Model

```bash
# Pull the Gemma 2B model (lightweight option)
ollama pull gemma2:2b

# Or pull Gemma 7B for better performance
ollama pull gemma2:7b

# Or pull Llama 3.1 8B
ollama pull llama3.1:8b
```

## Installation

Install the Datapizza AI OpenAI-like client:

```
pip install datapizza-ai-clients-openai-like
```

## Basic Usage

Here's a simple example of how to use Datapizza AI with Ollama:

```python
import os
from datapizza.clients.openai_like import OpenAILikeClient
from dotenv import load_dotenv

load_dotenv()

# Create client for Ollama
client = OpenAILikeClient(
    api_key="",  # Ollama doesn't require an API key
    model="gemma2:2b",  # Use any model you've pulled with Ollama
    system_prompt="You are a helpful assistant.",
    base_url="http://localhost:11434/v1",  # Default Ollama API endpoint
)

# Simple query
response = client.invoke("What is the capital of France?")
print(response.content)
```
