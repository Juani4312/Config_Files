# ─── Meta ───────────────────────────────────────────────────────
# Created by Phunt_Vieg_
# Ensure running interactively
[[ $- != *i* ]] && return


export XDG_DATA_DIRS="/var/lib/flatpak/exports/share:$XDG_DATA_DIRS"


# ─── History ─────────────────────────────────────────────────────
HISTSIZE=5000
HISTFILE=~/.zsh_history
SAVEHIST=$HISTSIZE
HISTDUP=erase
setopt appendhistory
setopt sharehistory

# ─── Keybinds ────────────────────────────────────────────────────
bindkey -e
bindkey "^[[1;5C" forward-word   # Ctrl + derecha
bindkey "^[[1;5D" backward-word  # Ctrl + izquierda
bindkey "^[[3;5~" kill-word      # Ctrl + Delete (borra palabra adelante)
bindkey "^[[3~"   delete-char    # Delete (borra caracter adelante)

# ─── FZF ─────────────────────────────────────────────────────────
eval "$(fzf --zsh)"
# FZF theme catppuccin
export FZF_DEFAULT_OPTS=" \
--color=bg+:#4a3826,bg:#2a2018,spinner:#e08030,hl:#f09040 \
--color=fg:#f5ede0,header:#e08030,info:#d4b896,pointer:#e08030 \
--color=marker:#c07838,fg+:#f5ede0,prompt:#e08030,hl+:#f09040 \
--color=selected-bg:#4a3826 \
--color=border:#5a4030,label:#f5ede0"
export FZF_TAB_COLORS='fg:#f5ede0,bg:#2a2018,hl:#e08030,min-height=5'

# ─── Zinit ───────────────────────────────────────────────────────
# Set the directory we want to store zinit and plugins
ZINIT_HOME="${ZDG_DATA_HOME:-${HOME}/.local/share}/zinit/zinit.git"
# Download Zinit, if it's not there yet
if [ ! -d "$ZINIT_HOME" ]; then
    mkdir -p "$(dirname $ZINIT_HOME)"
    git clone https://github.com/zdharma-continuum/zinit.git "$ZINIT_HOME"
fi
source "${ZINIT_HOME}/zinit.zsh"

# Add in zsh plugins
zinit light zsh-users/zsh-syntax-highlighting
zinit light zsh-users/zsh-completions
zinit light zsh-users/zsh-autosuggestions
zinit light Aloxaf/fzf-tab

# ─── Completion ──────────────────────────────────────────────────
autoload -Uz compinit && compinit
zinit cdreplay -q

# Completion styling
zstyle ':completion:*' matcher-list 'm:{A-Za-z}={A-Za-z}'
zstyle ':completion:*' list-colors "${(s.:.)LS_COLORS}"
zstyle ':completion:*' menu no
zstyle ':fzf-tab:*' use-fzf-default-opts yes
zstyle ':fzf-tab:*' fzf-flags --height=17
zstyle ':fzf-tab:complete:*' fzf-preview '
if [ -d "$realpath" ]; then
    eza --icons --tree --level=2 --color=always "$realpath"
elif [ -f "$realpath" ]; then
    bat -n --color=always --line-range :500 "$realpath"
fi
'

# ─── Aliases ─────────────────────────────────────────────────────
alias ls='eza --icons --color=always'
alias ll='eza --icons --color=always -l'
alias la='eza --icons --color=always -a'
alias lla='eza --icons --color=always -la'
alias lt='eza --icons --color=always -a --tree --level=1'
alias grep='grep --color=always'
alias vim='nvim'
alias vk='NVIM_APPNAME=nvim-kickstart nvim'   # Neovim con kickstart.nvim (para aprender)
alias lzg='lazygit'
alias lzd='lazydocker'
alias cbonsai='cbonsai -l -i -w 1'
alias ms='cd /mnt/1,8TB/Music'

# ─── Python Venv Functions ─────────────────────────────────────────
_activate_venv() { 
    if [[ -f "$1/bin/activate" ]]; then
        source "$1/bin/activate"
    else
        echo "Error: Virtual environment not found at '$1'."
    fi
}

mkvenv() {
    local name="${1:-.venv}"
    if [[ ! -d "$name" ]]; then
        python3 -m venv "$name" || return 1
    fi

    _activate_venv "$name"
}

venv() { _activate_venv "${1:-.venv}" }
pwnvenv() { _activate_venv "$HOME/pwndbg/.venv" }

# ─── Tools Init ──────────────────────────────────────────────────
# Setup bat (better than cat)
export BAT_THEME="base16"
alias bat='bat --paging=never'

# Setup zoxide (better than cd)
eval "$(zoxide init zsh)"

# Allowing comments in interactive zsh commands
setopt interactivecomments


# Pokemon startup
pokemon-colorscripts --no-title -s -r

# Initialize Oh-My-Posh
eval "$(oh-my-posh init zsh --config ~/.config/ohmyposh/viet.omp.json)"
export PATH="$HOME/.local/bin:$PATH"
