FROM node:22-slim

# ripgrep: opencode's search tool shells out to it (same as the Homebrew
# formula's dependency on the host). git/ca-certificates: general opencode
# runtime needs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ripgrep git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Pinned to match the host's installed version (1.17.6) so benchmark output
# isn't confounded by opencode-version differences between host and
# container runs. Bump deliberately, in step with the host install.
RUN npm install -g opencode-ai@1.17.6

COPY opencode.json /opt/opencode-config/opencode.json
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /root
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["sleep", "infinity"]
