FROM node:22-slim

# ripgrep: pi's search tooling shells out to it. curl: used by the
# entrypoint's reachability probe against the host's model server.
# git/ca-certificates: general runtime needs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ripgrep git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Pinned to match the host's installed version (0.83.0) so benchmark output
# isn't confounded by harness-version differences between host and container
# runs. Bump deliberately, in step with the host install.
RUN npm install -g @earendil-works/pi-coding-agent@0.83.0

# The llama.cpp provider is NOT built into pi - it comes from this package,
# which registers a provider named `llama-cpp` (hyphen) and reads
# LLAMA_BASE_URL from the environment (default http://localhost:8080).
# Without it, `pi --list-models` reports "No models available" no matter what
# LLAMA_BASE_URL or auth.json say - verified on a clean pi home.
#
# Installed under a staging HOME because /root is a named volume at runtime,
# which would mask anything written there during build. entrypoint.sh copies
# it across on first boot.
ENV PI_STAGE_HOME=/opt/pi-home
RUN mkdir -p "$PI_STAGE_HOME" \
    && HOME="$PI_STAGE_HOME" pi install git:github.com/huggingface/pi-llama

# No model config is baked into the image: the provider discovers models
# from the router at runtime, so the host's presets.ini is the only place
# models are declared - nothing here to keep in sync with it.
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /root
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["sleep", "infinity"]
