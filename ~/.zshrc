export FIREWORKS_API_KEY='fw_3ZJ6noctWy5VwT3SYYRX1srV'
export PATH="$PATH:/Applications/Docker.app/Contents/Resources/bin"
export PATH="$PATH:$HOME/.docker/bin"

. "$HOME/.local/bin/env"

# bun completions
[ -s "/Users/jarredrobidoux/.bun/_bun" ] && source "/Users/jarredrobidoux/.bun/_bun"

# bun
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

# >>> pyenv setup >>>
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
# <<< pyenv setup <<< 